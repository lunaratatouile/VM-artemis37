import pygame
import re
import os

class Formatage:
    warning = "[!] "
    error = "[X] "
    success = "[+] "
    info = "[i] "

f = Formatage

def to_8bits(valeur):
    """Force la valeur à rester sur 8 bits (modulo 256)."""
    return int(valeur) % 256

class Memoire:
    def __init__(self, taille):
        self.memoire = [0] * taille

    def __getitem__(self, adresse):
        if not isinstance(adresse, int):
            raise ValueError(f.error + f"L'adresse doit être un entier. Adresse reçue : {adresse}")
        if not 0 <= adresse < len(self.memoire):
            raise IndexError(f.error + f"Adresse hors des limites : {adresse}")
        return to_8bits(self.memoire[adresse])

    def __setitem__(self, adresse, valeur):
        if not isinstance(adresse, int):
            raise ValueError(f.error + f"L'adresse doit être un entier. Adresse reçue : {adresse}")
        if not 0 <= adresse < len(self.memoire):
            raise IndexError(f.error + f"Adresse hors des limites : {adresse}")
        self.memoire[adresse] = to_8bits(valeur)

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

class CPU:
    def __init__(self, screen, font):
        self.disk = Memoire(4096)
        self.ram = Memoire(4096)
        self.registres = {'clavier': 0}
        self.rip = 0
        self.pile = []
        self.stdout_renderer = PygameOutput(screen, font, (255, 255, 255), (10, 10))
        self.programme = []
        self.etiquettes = {}
        self.debug_info = []  # Stocker les informations de débogage

    def detect_type(self, data):
        if data.isdigit():
            return "INT"
        if isinstance(data, str):
            if data.startswith('0r'):
                return "REG"
            if data.startswith('0x'):
                return "RAM"
            if data.startswith('0d'):
                return "DISK"
            return "STR"
        raise TypeError(f"data \"{data}\" not supported")

    def stdout(self, data="0x0"):
        # Nettoyer l'argument pour supprimer les commentaires éventuels
        data = data.split(';')[0].strip()
        match self.detect_type(data):
            case "REG":
                retour_valeur = to_8bits(self.registres[data[2:]])
            case "RAM":
                retour_valeur = to_8bits(self.ram[int(data, 16)])
            case "DISK":
                retour_valeur = to_8bits(self.disk[int(data, 16)])
            case "INT":
                retour_valeur = to_8bits(int(data))
            case _:
                raise ValueError("\n" + f"Entrée invalide stdout: {data}")

        # Vérifier si la valeur est un caractère valide
        if not (0 <= retour_valeur <= 0x10FFFF):
            raise ValueError("\n" + f.error + f"Valeur Unicode invalide : {retour_valeur}")
        elif retour_valeur == 0:  # Ignorer les caractères vides ou non valides
            print("\n" + f.warning + f"Aucun caractère valide à afficher. (code ascii: {retour_valeur})")
            return

        self.stdout_renderer.write(chr(retour_valeur))

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
        match self.detect_type(src):
            case "REG":
                valeur = to_8bits(self.registres[src[2:]])
            case "RAM":
                valeur = to_8bits(self.ram[int(src, 16)])
            case "DISK":
                valeur = to_8bits(self.disk[int(src, 16)])
            case "INT":
                valeur = to_8bits(int(src))
            case "STR":
                valeur = to_8bits(ord(str(src)[0]))  # Prend le code ASCII du premier caractère
            case _:
                raise ValueError(f"Entrée invalide mov: {src}")

        match self.detect_type(dest):
            case "REG":
                self.registres[dest[2:]] = to_8bits(valeur)
            case "RAM":
                self.ram[int(dest, 16)] = to_8bits(valeur)
            case "DISK":
                self.disk[int(dest, 16)] = to_8bits(valeur)
            case _:
                raise ValueError(f"Destination invalide mov: {dest}")

    def set(self, dest, src):
        match self.detect_type(src):
            case "INT":
                valeur = to_8bits(src)
            case "STR":
                valeur = to_8bits(ord(str(src)[0]))  # Prend le code ASCII du premier caractère
            case _:
                raise ValueError(f"Entrée invalide set: {src}")

        match self.detect_type(dest):
            case "REG":
                self.registres[dest[2:]] = to_8bits(valeur)
            case "RAM":
                self.ram[int(dest, 16)] = to_8bits(valeur)
            case "DISK":
                self.disk[int(dest, 16)] = to_8bits(valeur)
            case _:
                raise ValueError(f"Destination invalide set: {dest}")

    def waitkey(self):
        """Attend qu'une touche soit pressée et la stocke dans le registre 'clavier'."""
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                if event.type == pygame.KEYDOWN:
                    self.registres['clavier'] = to_8bits(event.key)
                    print(f.info + f"Touche capturée: {event.key}")
                    return
            pygame.display.flip()
            clock.tick(60)

    def executer(self):
        log_file_path = os.path.join(os.path.dirname(__file__), "logs_execution.txt")
        log_entry = []
        while self.rip < len(self.programme):
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
                match op:
                    case 'stdout':
                        self.stdout(args[0])
                    case 'stdoutflush':
                        self.stdout_renderer.buffer = ""  # Réinitialise la chaîne unique pour un nouvel affichage
                    case 'jmp':
                        self.rip = self.etiquettes[args[0]]
                        continue
                    case 'call':
                        self.pile.append(self.rip + 1)
                        self.rip = self.etiquettes[args[0]]
                        continue
                    case 'mov':
                        self.mov(*args)
                    case 'set':
                        self.set(*args)
                    case 'waitkey':
                        self.waitkey()
                    case 'ret':
                        self.rip = self.pile.pop() if self.pile else len(self.programme)
                    case _:
                        raise ValueError(f"Instruction inconnue : {op}")
            except Exception as e:
                print(f.error + f"Erreur lors de l'exécution de l'instruction {instr}: {e}")
                break
            self.rip += 1
            clock.tick(60)

        with open(log_file_path, "w") as log_file:
            log_file.write(''.join(log_entry))
            if len(self.debug_info) <= 10:
                print(f.success + ''.join(log_entry).strip())

        print(f.info + f"Les instructions complètes sont enregistrées dans le fichier '{log_file_path}'.")

    def afficher_etat(self):
        print(f.info + f"Program ended at RIP: {self.rip} ( instruction {self.programme[self.rip-1] if self.rip > 0 else 'N/A'})")
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
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24)

    programme = """
    start_line:
    stdoutflush
    stdout 36    ; $
    stdout 115   ; s
    stdout 104   ; h
    stdout 101   ; e
    stdout 108   ; l
    stdout 108   ; l
    stdout 58    ;  
    stdout 32    ; :

    save_key:
    waitkey      ; <-- Attend une touche
    ; addbuffer 0bprompt 0rclavier (non implémenté ici)
    
    show_buffer_keys:
    ; stdout 0bprompt (non implémenté ici)

    startvm:
    call start_line
    call save_key
    call show_buffer_keys

    end:
    ret
    """
    cpu = CPU(screen, font)
    cpu.charger_programme(programme)
    cpu.executer()
    cpu.afficher_etat()
    pygame.quit()
