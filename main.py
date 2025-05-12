import pygame
import re
import os
import threading

class Formatage:
    warning = "[!] "
    error = "[X] "
    success = "[+] "
    info = "[i] "

f = Formatage

class Memoire:
    def __init__(self, taille):
        self.memoire = [0] * taille

    def __getitem__(self, adresse):
        if not isinstance(adresse, int):
            raise ValueError(f.error + f"L'adresse doit être un entier. Adresse reçue : {adresse}")
        if not 0 <= adresse < len(self.memoire):
            raise IndexError(f.error + f"Adresse hors des limites : {adresse}")
        return self.memoire[adresse]

    def __setitem__(self, adresse, valeur):
        if not isinstance(adresse, int):
            raise ValueError(f.error + f"L'adresse doit être un entier. Adresse reçue : {adresse}")
        if not 0 <= adresse < len(self.memoire):
            raise IndexError(f.error + f"Adresse hors des limites : {adresse}")
        self.memoire[adresse] = valeur

class PygameOutput:
    def __init__(self, screen, font, color, pos):
        self.screen = screen
        self.font = font
        self.color = color
        self.pos = pos
        self.buffer = ""  # Utilisation d'une chaîne unique pour le texte

    def write(self, text):
        if not isinstance(text, str):
            raise ValueError(f.error + f"Le texte à écrire doit être une chaîne de caractères. Reçu : {text}")
        # Filtrer les caractères nuls
        text = text.replace('\x00', '')
        self.buffer += text  # Ajouter le texte à la chaîne unique
        self.render()

    def render(self):
        x, y = self.pos
        self.screen.fill((0, 0, 0))  # Efface l'écran une seule fois
        # Afficher tout le texte sur une seule ligne
        for char in self.buffer:
            rendered_char = self.font.render(char, True, self.color)
            self.screen.blit(rendered_char, (x, y))
            x += rendered_char.get_width()
        pygame.display.flip()

class ClavierManager:
    def __init__(self):
        self._dernier_code_touche = 0
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None

    def demarrer(self):
        self._thread = threading.Thread(target=self._boucle_clavier, daemon=True)
        self._thread.start()

    def arreter(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join()

    def _boucle_clavier(self):
        while not self._stop_event.is_set():
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    code = 0
                    if event.key == pygame.K_RETURN:
                        code = ord('\n')
                    elif event.key == pygame.K_BACKSPACE:
                        code = ord('\b')
                    elif pygame.K_SPACE <= event.key <= pygame.K_z:
                        code = event.key
                    if code:
                        with self._lock:
                            self._dernier_code_touche = code
            pygame.time.wait(100)

    def lire_touche(self):
        with self._lock:
            code = self._dernier_code_touche
            self._dernier_code_touche = 0
        return code

class CPU:
    def __init__(self, screen, font, clavier_manager):
        self.disk = Memoire(4096)
        self.ram = Memoire(4096)
        self.registres = {'clavier': 0}
        self.rip = 0
        self.pile = []
        self.stdout_renderer = PygameOutput(screen, font, (255, 255, 255), (10, 10))
        self.programme = []
        self.etiquettes = {}
        self.debug_info = []  # Stocker les informations de débogage
        self.clavier_manager = clavier_manager

    def stdout(self, data="0x0"):
        # Nettoyer l'argument pour supprimer les commentaires éventuels
        data = data.split(';')[0].strip()
        if isinstance(data, str) and data.startswith('0r'):
            retour_valeur = self.registres[data[2:]]
        elif isinstance(data, str) and data.startswith('0x'):
            retour_valeur = int(data, 16)
        else:
            retour_valeur = int(data)

        # Vérifier si la valeur est un caractère valide
        if not (0 <= retour_valeur <= 0x10FFFF):
            raise ValueError(f.error + f"Valeur Unicode invalide : {retour_valeur}")
        elif retour_valeur == 0:  # Ignorer les caractères vides ou non valides
            print(f.warning + f"Aucun caractère valide à afficher. (code ascii: {retour_valeur})")
            return

        char = chr(retour_valeur)
        # Gestion du backspace dans le buffer
        if char == '\b':
            self.stdout_renderer.buffer = self.stdout_renderer.buffer[:-1]
            self.stdout_renderer.render()
        else:
            self.stdout_renderer.write(char)

    def charger_programme(self, programme_str):
        lignes = programme_str.strip().split('\n')
        programme = []
        for ligne in lignes:
            ligne = ligne.strip()
            if not ligne or ligne.startswith(';'):
                continue
            if ':' in ligne and not ligne.split(':')[1].strip():
                etiquette = ligne.replace(':', '').strip()
                programme.append(('etiquette', etiquette))
                continue
            tokens = re.split(r'\s+', ligne, maxsplit=1)
            instr = tokens[0]
            args = tokens[1].split(',') if len(tokens) > 1 else []
            # Nettoyer les arguments en supprimant les commentaires
            args = [arg.split(';')[0].strip() for arg in args]
            programme.append((instr, *args))
        self.programme = [instr for instr in programme if instr[0] != 'etiquette']
        self.etiquettes = {instr[1]: i for i, instr in enumerate(programme) if instr[0] == 'etiquette'}

    def afficher_etat_registres(self):
        print("=== État des registres ===")
        for registre, valeur in self.registres.items():
            print(f.success + f"{registre}: {valeur}")
        print("==========================")

    def mov(self, dest, src):
        # Si la source est un registre
        if isinstance(src, str) and src.startswith('0r'):
            valeur = self.registres[src[2:]]
        # Si la source est une valeur immédiate (ex: 0x10 ou 42)
        elif isinstance(src, str) and src.startswith('0x'):
            valeur = int(src, 16)
        else:
            valeur = int(src)

        # Si la destination est un registre
        if dest in self.registres:
            self.registres[dest] = valeur
        # Si la destination est une adresse mémoire
        elif dest.isdigit():
            self.ram[int(dest)] = valeur
        else:
            raise ValueError(f"Destination invalide : {dest}")

    def capturer_touche(self):
        return self.clavier_manager.lire_touche()

    def interruptions(self):
        self.registres['clavier'] = self.capturer_touche()

    def executer(self):
        log_file_path = os.path.join(os.path.dirname(__file__), "logs_execution.txt")
        log_entry = []
        clock = pygame.time.Clock()
        while self.rip < len(self.programme):
            self.interruptions()  # Gérer les interruptions

            # On ne gère que la fermeture de la fenêtre ici
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    print(f.success + "Fermeture de la machine virtuelle.")
                    return

            instr = self.programme[self.rip]
            op = instr[0]
            args = instr[1:]
            log_entry.append(f"Instruction exécutée : {instr}\n")
            self.debug_info.append(log_entry[-1])

            try:
                if op == 'stdout':
                    self.stdout(args[0])
                elif op == 'stdoutflush':
                    self.stdout_renderer.buffer = ""  # Réinitialise la chaîne unique pour un nouvel affichage
                    self.stdout_renderer.render()
                elif op == 'jmp':
                    self.rip = self.etiquettes[args[0]]
                    continue
                elif op == 'call':
                    self.pile.append(self.rip + 1)
                    self.rip = self.etiquettes[args[0]]
                    continue
                elif op == 'mov':
                    self.mov(*args)
                elif op == 'ret':
                    self.rip = self.pile.pop() if self.pile else len(self.programme)
                else:
                    raise ValueError(f"Instruction inconnue : {op}")
            except Exception as e:
                print(f.error + f"Erreur lors de l'exécution de l'instruction {instr}: {e}")
                break
            self.rip += 1
            # Limiter à 60 FPS
            clock.tick(60)

        with open(log_file_path, "w") as log_file:
            log_file.writelines(log_entry)
            if len(self.debug_info) <= 10:
                print(''.join(log_entry).strip())

        print(f.info + f"\nLes instructions complètes sont enregistrées dans le fichier '{log_file_path}'.")

    def afficher_etat(self):
        print(f.info + f"Program ended at RIP: {self.rip} ( instruction {self.programme[self.rip] if self.rip < len(self.programme) else 'END'})")
        print("\n=== Registres : ===")
        for registre, valeur in self.registres.items():
            print(f.success + f"{registre}: {valeur}")
        print("\n=== Informations de débogage ===")
        for info in self.debug_info[:10]:  # Affiche uniquement les 10 premières instructions
            print(f.success + info.strip())
        print(f.info + f"Les instructions complètes sont disponibles dans le fichier 'logs_execution.txt'.")

if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Machine Virtuelle avec Pygame")
    font = pygame.font.Font(None, 24)

    programme = """
print_hello:
stdoutflush
stdout 72    ; H
stdout 101   ; e
stdout 108   ; l
stdout 108   ; l
stdout 111   ; o
stdout 32    ; (espace)
stdout 87    ; W
stdout 111   ; o
stdout 114   ; r
stdout 108   ; l
stdout 100   ; d
stdout 33    ; !
stdout 0rclavier

startvm:
call print_hello

end:
ret
"""

    clavier_manager = ClavierManager()
    clavier_manager.demarrer()

    cpu = CPU(screen, font, clavier_manager)
    cpu.charger_programme(programme)
    cpu.executer()
    cpu.afficher_etat()

    clavier_manager.arreter()
    pygame.quit()
