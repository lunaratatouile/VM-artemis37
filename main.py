import pygame
import re

class Memoire:
    def __init__(self, taille):
        self.memoire = [0] * taille

    def __getitem__(self, adresse):
        if not isinstance(adresse, int):
            raise ValueError(f"L'adresse doit être un entier. Adresse reçue : {adresse}")
        return self.memoire[adresse]

    def __setitem__(self, adresse, valeur):
        if not isinstance(adresse, int):
            raise ValueError(f"L'adresse doit être un entier. Adresse reçue : {adresse}")
        self.memoire[adresse] = valeur

class PygameOutput:
    def __init__(self, screen, font, color, pos):
        self.screen = screen
        self.font = font
        self.color = color
        self.pos = pos
        self.buffer = []

    def write(self, text):
        # Filtrer les caractères nuls
        text = text.replace('\x00', '')
        self.buffer.append(text)
        if len(self.buffer) > 20:  # Limiter l'affichage à 20 lignes
            self.buffer.pop(0)
        self.render()

    def render(self):
        self.screen.fill((0, 0, 0))  # Effacer l'écran
        y_offset = self.pos[1]
        for line in self.buffer:
            rendered_line = self.font.render(line.strip(), True, self.color)
            self.screen.blit(rendered_line, (self.pos[0], y_offset))
            y_offset += rendered_line.get_height()
        pygame.display.flip()

class CPU:
    def __init__(self, screen, font):
        self.disk = Memoire(4096)
        self.ram = Memoire(4096)
        self.registres = {'rax': 0, 'rcx': 0}
        self.rip = 0
        self.pile = []
        self.stdout_renderer = PygameOutput(screen, font, (255, 255, 255), (10, 10))
        self.programme = []
        self.etiquettes = {}
        self.debug_info = []  # Stocker les informations de débogage


    def stdout(self, data="0x0"):
        # Nettoyer l'argument pour supprimer les commentaires éventuels
        data = data.split(';')[0].strip()
        if data in self.registres:
            retour_valeur = self.registres[data]
        elif isinstance(data, str) and data.startswith('0x'):
            retour_valeur = int(data, 16)
        else:
            retour_valeur = int(data)

        # Ajouter la sortie à l'affichage Pygame
        self.stdout_renderer.write(chr(retour_valeur))

    def charger_programme(self, programme_str):
        lignes = programme_str.strip().split('\n')
        programme = []
        for ligne in lignes:
            ligne = ligne.strip()
            if not ligne or ligne.startswith(';'):
                continue
            if ':' in ligne:
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
        """
        Affiche l'état actuel des registres.
        """
        print("=== État des registres ===")
        for registre, valeur in self.registres.items():
            print(f"{registre}: {valeur}")
        print("==========================")

    def executer(self):
        while self.rip < len(self.programme):
            instr = self.programme[self.rip]

            op = instr[0]
            args = instr[1:]
            self.debug_info.append(f"Instruction exécutée : {instr}")  # Ajouter au débogage

            if op == 'stdout':
                # Limiter les arguments à un seul (corriger l'appel)
                self.stdout(args[0])
            elif op == 'jmp':
                self.rip = self.etiquettes[args[0]]
                continue
            elif op == 'call':
                self.pile.append(self.rip + 1)
                self.rip = self.etiquettes[args[0]]
                continue
            elif op == 'ret':
                self.rip = self.pile.pop() if self.pile else len(self.programme)
            else:
                print(f"Instruction inconnue : {op}")
            self.rip += 1
        # Affichage des états
        self.afficher_etat_registres()  # Affiche les registres après chaque instruction


    def afficher_etat(self):
        print(f"Program ended at RIP: {self.rip}")
        print(f"Pile (stack) : {self.pile}")
        print("Registres :")
        for registre, valeur in self.registres.items():
            print(f"{registre}: {valeur}")
        print("\n=== Informations de débogage ===")
        for info in self.debug_info:
            print(info)


if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Machine Virtuelle avec Pygame")
    font = pygame.font.Font(None, 24)

    programme = """
    start:
    call print_hello
    print_hello:
    stdout 72    ; H
    stdout 101   ; e
    stdout 108   ; l
    stdout 108   ; l
    stdout 111   ; o
    stdout 44    ; ,
    stdout 32    ; (espace)
    stdout 87    ; W
    stdout 111   ; o
    stdout 114   ; r
    stdout 108   ; l
    stdout 100   ; d
    stdout 33    ; !
    """
    cpu = CPU(screen, font)
    cpu.charger_programme(programme)
    cpu.executer()
    cpu.afficher_etat()
    pygame.quit()
