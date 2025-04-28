import re

class Memoire:
    def __init__(self, taille):
        self.memoire = [0] * taille

    def __getitem__(self, adresse):
        return self.memoire[int(adresse, 16)]

    def __setitem__(self, adresse, valeur):
        self.memoire[int(adresse, 16)] = valeur

class Registres:
    def __init__(self):
        self.registres = {
            'rax': 0,
            'rsi': 0,
            'rsp': 0x7FFF,
            'rip': 0,
            'rcx': 0,
            'rdx': 0,
            'rdi': 0
        }

    def __getitem__(self, reg):
        return self.registres.get(reg, 0)

    def __setitem__(self, reg, valeur):
        self.registres[reg] = valeur

class CPU:
    def __init__(self):
        self.disk = Memoire(4096)
        self.ram = Memoire(4096)
        self.registres = Registres()
        self.pile = []
        self.etiquettes = {}

    def mov(self, dest, src):
        if src in self.registres.registres:
            valeur = self.registres[src]
        elif src.startswith('0x'):
            valeur = int(src, 16)
        else:
            try:
                valeur = int(src)
            except:
                valeur = src
        if dest.startswith('0x'):
            self.ram[dest] = valeur
        else:
            self.registres[dest] = valeur

    def xor(self, reg1, reg2):
        val1 = self.registres[reg1]
        val2 = self.registres[reg2]
        self.registres[reg1] = val1 ^ val2

    def pop(self, reg):
        if self.pile:
            valeur = self.pile.pop()
            self.registres[reg] = valeur

    def jmp(self, etiquette):
        self.registres['rip'] = self.etiquettes[etiquette]

    def call(self, etiquette):
        self.pile.append(self.registres['rip'] + 1)
        self.jmp(etiquette)

    def ret(self):
        if self.pile:
            retour = self.pile.pop()
            self.registres['rip'] = retour
        else:
            # Fin du programme si pile vide (retour du main)
            self.registres['rip'] = len(self.programme)

    def charger_programme(self, programme_str):
        lignes = programme_str.strip().split('\n')
        programme = []
        for idx, ligne in enumerate(lignes):
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
        for idx, instr in enumerate(programme):
            if instr[0] == 'etiquette':
                self.etiquettes[instr[1]] = len(code_sans_etiquettes)
            else:
                code_sans_etiquettes.append(instr)
        self.programme = code_sans_etiquettes

    def executer(self):
        while self.registres['rip'] < len(self.programme):
            instr = self.programme[self.registres['rip']]
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
                self.pile.append(instr[1])
            self.registres['rip'] += 1

# Exemple : fonction qui additionne deux valeurs et retourne le résultat via rax
programme_asm = """
; Programme principal
start:
    mov rsi, 5
    mov rdi, 7
    call addition
    ; rax contient maintenant 12
    jmp end

addition:
    mov rax, rsi
    xor rax, rdi   ; Pour l'exemple, mettons rax = rsi ^ rdi (XOR), pas addition réelle
    ret

end:
"""

cpu = CPU()
cpu.charger_programme(programme_asm)
cpu.executer()

print("Registres après exécution :")
for reg, val in cpu.registres.registres.items():
    print(f"{reg}: {val}")
print("Pile :", cpu.pile)
print("Résultat retourné par la fonction (rax):", cpu.registres['rax'])
