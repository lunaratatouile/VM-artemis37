import re

class Memoire:
    def __init__(self, taille):
        self.memoire = [0] * taille

    def __getitem__(self, adresse):
        return self.memoire[int(adresse, 16)]

    def __setitem__(self, adresse, valeur):
        self.memoire[int(adresse, 16)] = valeur

class CPU:
    def __init__(self):
        self.disk = Memoire(4096)
        self.ram = Memoire(4096)
        self.pile = []
        self.etiquettes = {}

    def mov(self, dest, src):
        # src peut être une adresse mémoire ou une valeur immédiate
        if isinstance(src, str) and src.startswith('0x'):
            valeur = self.ram[src]
        else:
            try:
                valeur = int(src)
            except:
                valeur = src
        self.ram[dest] = valeur

    def xor(self, dest, src):
        val1 = self.ram[dest]
        val2 = self.ram[src]
        self.ram[dest] = val1 ^ val2

    def pop(self, dest):
        if self.pile:
            self.ram[dest] = self.pile.pop()

    def jmp(self, etiquette):
        self.ram['0xRIP'] = self.etiquettes[etiquette]

    def call(self, etiquette):
        self.pile.append(self.ram['0xRIP'] + 1)
        self.jmp(etiquette)

    def ret(self):
        if self.pile:
            retour = self.pile.pop()
            self.ram['0xRIP'] = retour
        else:
            self.ram['0xRIP'] = len(self.programme)

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
            args = []
            if len(tokens) > 1:
                args = [a.strip() for a in tokens[1].split(',')]
            programme.append(tuple([instr] + args))
        # Indexation des étiquettes
        self.etiquettes.clear()
        code_sans_etiquettes = []
        for instr in programme:
            if instr[0] == 'etiquette':
                self.etiquettes[instr[1]] = len(code_sans_etiquettes)
            else:
                code_sans_etiquettes.append(instr)
        self.programme = code_sans_etiquettes
        self.ram['0xRIP'] = 0  # Instruction pointer en RAM

    def executer(self):
        while self.ram['0xRIP'] < len(self.programme):
            instr = self.programme[self.ram['0xRIP']]
            op = instr[0]
            if op == 'mov':
                self.mov(*instr[1:])
            elif op == 'xor':
                self.xor(*instr[1:])
            elif op == 'pop':
                self.pop(*instr[1:])
            elif op == 'jmp':
                self.jmp(*instr[1:])
                continue
            elif op == 'call':
                self.call(*instr[1:])
                continue
            elif op == 'ret':
                self.ret()
                continue
            elif op == 'db':
                # Données brutes, on les "pousse" sur la pile
                self.pile.append(instr[1])
            self.ram['0xRIP'] += 1

# Exemple de programme (addition de deux cases mémoire)
programme_asm = """
; Stocker 5 à l'adresse 0x10 et 7 à 0x11
mov 0x10, 5
mov 0x11, 7
call addition
jmp end

addition:
    mov 0x12, 0x10
    xor 0x12, 0x11   ; 0x12 = 0x10 ^ 0x11 (XOR pour l'exemple)
    ret 0x12

end:
"""

cpu = CPU()
cpu.charger_programme(programme_asm)
cpu.executer()

print("RAM (adresses 0x10, 0x11, 0x12) :")
for addr in ['0x10', '0x11', '0x12']:
    print(f"{addr}: {cpu.ram[addr]}")
print("Pile :", cpu.pile)
