import re
import os
import keyboard

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

    def afficher_etat(self):
        print("RAM (adresses utilisées) :")
        for addr in range(len(self.memoire)):
            if self.memoire[addr] != 0:
                print(f"0x{addr:X}: {self.memoire[addr]}")

class CPU:
    def __init__(self):
        self.disk = Memoire(4096)
        self.ram = Memoire(4096)
        self.pile = []
        self.etiquettes = {}
        self.registres = {
            'rax': 0,  # Registre pour les retours
            'rcx': 0,  # Registre pour stocker le code ASCII du caractère
        }
        self.rip = 0  # Pointeur d'instruction (entier)
        self.stdout = []  # Capturer les sorties
        self.debug_info = []  # Stocker les informations de débogage

    def ret(self, data="0x0"):
        """
        Gère l'instruction 'ret'.
        Si 'data' est un registre valide, utilise sa valeur.
        Sinon, essaie de convertir directement.
        """
        if data in self.registres:
            retour_valeur = self.registres[data]
        elif isinstance(data, str) and data.startswith("0x"):
            retour_valeur = int(data, 16)
        else:
            retour_valeur = int(data)

        self.registres['rax'] = retour_valeur
        if self.pile:
            self.rip = self.pile.pop()
        else:
            self.rip = len(self.programme)
            
    def stdout(self, data="0x0"):
        """
        Gère l'instruction 'ret'.
        Si 'data' est un registre valide, utilise sa valeur.
        Sinon, essaie de convertir directement.
        """
        if data in self.registres:
            retour_valeur = self.registres[data]
        elif isinstance(data, str) and data.startswith("0x"):
            retour_valeur = int(data, 16)
        else:
            retour_valeur = int(data)

        self.stdout.append(retour_valeur)
        if self.pile:
            self.rip = self.pile.pop()
        else:
            self.rip = len(self.programme)

    def charger_programme(self, programme_str):
        lignes = programme_str.strip().split('\n')
        programme = []
        for ligne in lignes:
            ligne = ligne.strip()
            if not ligne or ligne.startswith(';'):
                continue
            ligne = ligne.split(';')[0].strip()
            if ':' in ligne:
                etiquette = ligne.replace(':', '').strip()
                programme.append(('etiquette', etiquette))
                continue
            tokens = re.split(r'\s+', ligne, maxsplit=1)
            instr = tokens[0]
            args = []
            if len(tokens) > 1:
                args = [a.strip() for a in tokens[1].split(',')]
            programme.append(tuple([instr] + args))
        self.etiquettes.clear()
        code_sans_etiquettes = []
        for instr in programme:
            if instr[0] == 'etiquette':
                self.etiquettes[instr[1]] = len(code_sans_etiquettes)
            else:
                code_sans_etiquettes.append(instr)
        self.programme = code_sans_etiquettes
        self.rip = 0

    def capturer_touche(self):
        """
        Capture une touche et met à jour le registre rcx avec son code ASCII.
        Affiche également la touche capturée.
        A CORRIGER: LE MAPPAGE DES TOUCHES DU CLAVIER EST BUGUE
        """
        event = keyboard.read_event()
        if event.event_type == keyboard.KEY_DOWN:
            key = event.name
            if key == 'enter':
                self.registres['rcx'] = ord('\n')  # Code ASCII pour Entrée
            elif key == 'backspace':
                self.registres['rcx'] = ord('\b')  # Code ASCII pour Retour arrière
            elif len(key) == 1 and 'a' <= key <= 'z':
                self.registres['rcx'] = ord(key)  # Code ASCII pour a-z
            else:
                print(f"Touche non gérée par l'interruption systeme clavier : {key}")

    def interruptions(self):
        """
        Gère les interruptions système, notamment la capture d'une touche.
        """
        self.capturer_touche()

    def afficher_etat_registres(self):
        """
        Affiche l'état actuel des registres.
        """
        print("=== État des registres ===")
        for registre, valeur in self.registres.items():
            print(f"{registre}: {valeur}")
        print("==========================")

    def afficher_stdout(self):
        """
        Affiche la sortie standard accumulée.
        """
        os.system('cls')
        print(''.join(chr(char) for char in self.stdout))

    def executer(self):
        while self.rip < len(self.programme):
            # Interruption système pour capturer les touches
            self.interruptions()

            # Récupération de l'instruction actuelle
            instr = self.programme[self.rip]
            op = instr[0]
            self.debug_info.append(f"Instruction exécutée : {instr}")  # Ajouter au débogage

            # Exécution des instructions
            if op == 'ret':
                self.ret(*instr[1:])
            if op == 'stdout':
                self.stdout(*instr[1:])
            elif op == 'jmp':
                self.rip = self.etiquettes[instr[1]]
                continue
            elif op == 'call':
                self.pile.append(self.rip + 1)
                self.rip = self.etiquettes[instr[1]]
                continue
            else:
                print(f"Instruction inconnue : {op}")

            # Avancement de l'instruction
            self.rip += 1
            self.afficher_stdout()

        # Affichage des états
        self.afficher_etat_registres()  # Affiche les registres après chaque instruction
        print("=== Sortie standard ===")
        self.afficher_stdout()         # Affiche la sortie standard accumulée
        print("=======================")

    def afficher_etat(self):
        print(f"Program ended at RIP: {self.rip}")
        print(f"Pile (stack) : {self.pile}")
        print("Registres :")
        for registre, valeur in self.registres.items():
            print(f"{registre}: {valeur}")
        print("\n=== Informations de débogage ===")
        for info in self.debug_info:
            print(info)


# Exemple d'utilisation
if __name__ == "__main__":
    programme = """
    start:
    call capture_input
    capture_input:
    stdout rcx
    jmp start
    """
    cpu = CPU()
    cpu.charger_programme(programme)
    cpu.executer()
    cpu.afficher_etat()
