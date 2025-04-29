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

    def mov(self, dest, src):
        if isinstance(src, str) and src.startswith('0x'):
            valeur = self.ram[int(src, 16)]
        else:
            valeur = int(src)
        self.ram[int(dest, 16)] = valeur

    def xor(self, dest, src):
        val1 = self.ram[int(dest, 16)]
        if isinstance(src, str) and src.startswith('0x'):
            val2 = self.ram[int(src, 16)]
        else:
            val2 = int(src)
        self.ram[int(dest, 16)] = val1 ^ val2

    def add(self, dest, src):
        val1 = self.ram[int(dest, 16)]
        if isinstance(src, str) and src.startswith('0x'):
            val2 = self.ram[int(src, 16)]
        else:
            val2 = int(src)
        self.ram[int(dest, 16)] = val1 + val2

    def sub(self, dest, src):
        val1 = self.ram[int(dest, 16)]
        if isinstance(src, str) and src.startswith('0x'):
            val2 = self.ram[int(src, 16)]
        else:
            val2 = int(src)
        self.ram[int(dest, 16)] = val1 - val2

    def pop(self, dest):
        if self.pile:
            self.ram[int(dest, 16)] = self.pile.pop()

    def jmp(self, etiquette):
        self.rip = self.etiquettes[etiquette]

    def call(self, etiquette):
        self.pile.append(self.rip + 1)
        self.jmp(etiquette)

    def ret(self, data="0x0"):
        if isinstance(data, str) and data.startswith("0x"):
            retour_valeur = int(data, 16)
        else:
            retour_valeur = int(data)

        # Affichage de la valeur retournée dans stdout
        self.stdout.append(retour_valeur)

        self.registres['rax'] = retour_valeur
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
            # Supprimer les commentaires
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
        self.rip = 0  # Initialiser RIP comme entier

    def capturer_touche(self):
        """Capture une touche et met à jour le registre rcx avec son code ASCII."""
        print("Appuyez sur une touche (a-z, Entrée ou Retour arrière)...")
        while True:
            event = keyboard.read_event()
            if event.event_type == keyboard.KEY_DOWN:
                key = event.name
                if key == 'enter':
                    self.registres['rcx'] = ord('\n')  # Code ASCII pour Entrée
                    break
                elif key == 'backspace':
                    self.registres['rcx'] = ord('\b')  # Code ASCII pour Retour arrière
                    break
                elif len(key) == 1 and 'a' <= key <= 'z':
                    self.registres['rcx'] = ord(key)  # Code ASCII pour a-z
                    break

    def interruptions(self):
        self.capturer_touche()

    def executer(self):
        while self.rip < len(self.programme):
            os.system('cls' if os.name == 'nt' else 'clear')  # Nettoyer l'écran
            instr = self.programme[self.rip]
            op = instr[0]
            self.debug_info.append(f"Instruction exécutée : {instr}")  # Ajouter au débogage

            if op == 'mov':
                self.mov(*instr[1:])
            elif op == 'xor':
                self.xor(*instr[1:])
            elif op == 'add':
                self.add(*instr[1:])
            elif op == 'sub':
                self.sub(*instr[1:])
            elif op == 'pop':
                self.pop(*instr[1:])
            elif op == 'jmp':
                self.jmp(*instr[1:])
                continue
            elif op == 'call':
                self.call(*instr[1:])
                continue
            elif op == 'ret':
                self.ret(*instr[1:])
                continue
            elif op == 'db':
                self.pile.append(int(instr[1], 16))
            else:
                print(f"Instruction inconnue : {op}")
            self.rip += 1

            self.interruptions()
            # Afficher l'état après chaque instruction
            print('Sortie (stdout) :', ''.join(map(str, self.stdout)))

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
    ret rcx
    jmp start
    """
    cpu = CPU()
    cpu.charger_programme(programme)
    cpu.executer()
    cpu.afficher_etat()
