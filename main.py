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
        self.buffer = ""

    def write(self, text):
        if not isinstance(text, str):
            raise ValueError(f.error + f"Le texte à écrire doit être une chaîne de caractères. Reçu : {text}")
        text = text.replace('\x00', '')
        self.buffer += text
        self.render()

    def render(self):
        x, y = self.pos
        self.screen.fill((0, 0, 0))
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
        self.buffers = {}
        self.rip = 0
        self.pile = []
        self.stdout_renderer = PygameOutput(screen, font, (255, 255, 255), (10, 10))
        self.programme = []
        self.etiquettes = {}
        self.debug_info = []

    def detect_type(self, data):
        if isinstance(data, int) or (isinstance(data, str) and data.isdigit()):
            return "INT"
        if isinstance(data, str):
            if data.startswith('0r'):
                return "REG"
            if data.startswith('0x'):
                return "RAM"
            if data.startswith('0d'):
                return "DISK"
            if data.startswith('0b'):
                return "BUFFER"
            return "STR"
        raise TypeError(f"data \"{data}\" not supported")

    def stdout(self, data="0x0"):
        data = data.split(';')[0].strip()
        texte = ""
        type_data = self.detect_type(data)
        match type_data:
            case "REG":
                reg_name = data[2:] if data.startswith('0r') else data
                if reg_name not in self.registres:
                    raise ValueError(f.error + f"Registre '{reg_name}' non initialisé.")
                retour_valeur = to_8bits(self.registres[reg_name])
                texte = chr(retour_valeur)
            case "RAM":
                retour_valeur = to_8bits(self.ram[int(data, 16)])
                texte = chr(retour_valeur)
            case "DISK":
                retour_valeur = to_8bits(self.disk[int(data, 16)])
                texte = chr(retour_valeur)
            case "INT":
                retour_valeur = to_8bits(int(data))
                texte = chr(retour_valeur)
            case "BUFFER":
                buffer_name = data
                if buffer_name not in self.buffers:
                    raise ValueError(f.error + f"Buffer '{buffer_name}' non initialisé.")
                texte = ''.join(chr(val) for val in self.buffers[buffer_name])
            case "STR":
                texte = str(data)
            case _:
                raise ValueError("\n" + f"Entrée invalide stdout: {data}")

        if texte:
            self.stdout_renderer.write(texte)
        else:
            print(f.warning + f"Aucun caractère valide à afficher.")

    def setbuffer(self, name):
        if not isinstance(name, str):
            raise ValueError(f.error + "Le nom du buffer doit être une chaîne de caractères.")
        if not name.startswith('0b'):
            raise ValueError(f.error + "Le nom du buffer doit commencer par '0b'.")
        self.buffers[name] = []

    def addbuffer(self, dest, src):
        if dest not in self.buffers:
            raise ValueError(f.error + f"Buffer '{dest}' non initialisé.")
        type_src = self.detect_type(src)
        match type_src:
            case "REG":
                reg_name = src[2:] if src.startswith('0r') else src
                if reg_name not in self.registres:
                    raise ValueError(f.error + f"Registre '{reg_name}' non initialisé.")
                valeur = to_8bits(self.registres[reg_name])
            case "RAM":
                valeur = to_8bits(self.ram[int(src, 16)])
            case "DISK":
                valeur = to_8bits(self.disk[int(src, 16)])
            case "INT":
                valeur = to_8bits(int(src))
            case "STR":
                if not src:
                    raise ValueError(f.error + "Impossible d'ajouter une chaîne vide au buffer.")
                valeur = to_8bits(ord(str(src)[0]))
            case _:
                raise ValueError(f"Entrée invalide addbuffer: {src}")
        self.buffers[dest].append(valeur)

    def charger_programme(self, programme_str):
        lignes = programme_str.strip().split('\n')
        programme = []
        etiquettes = {}
        for idx, ligne in enumerate(lignes):
            ligne = ligne.strip()
            if not ligne or ligne.startswith(';'):
                continue
            if ':' in ligne and not ligne.split(':')[1].strip():
                etiquette = ligne.replace(':', '').strip()
                etiquettes[etiquette] = len(programme)
                continue
            tokens = re.split(r'\s+', ligne, maxsplit=1)
            instr = tokens[0]
            args_str = tokens[1] if len(tokens) > 1 else ''
            args_str = args_str.split(';')[0]
            # Séparation par virgule OU espace(s)
            args = [arg.strip() for arg in re.split(r'[,\s]+', args_str) if arg.strip()]
            programme.append((instr, *args))
        self.programme = programme
        self.etiquettes = etiquettes

    def afficher_etat_registres(self):
        print("=== État des registres ===")
        for registre, valeur in self.registres.items():
            print(f.success + f"{registre}: {valeur}")
        print("==========================")

    def mov(self, dest, src):
        src_type = self.detect_type(src)
        match src_type:
            case "REG":
                reg_name = src[2:] if src.startswith('0r') else src
                if reg_name not in self.registres:
                    raise ValueError(f.error + f"Registre '{reg_name}' non initialisé.")
                valeur = to_8bits(self.registres[reg_name])
            case "RAM":
                valeur = to_8bits(self.ram[int(src, 16)])
            case "DISK":
                valeur = to_8bits(self.disk[int(src, 16)])
            case "INT":
                valeur = to_8bits(int(src))
            case "STR":
                valeur = to_8bits(ord(str(src)[0]))
            case _:
                raise ValueError(f"Entrée invalide mov: {src}")

        dest_type = self.detect_type(dest)
        match dest_type:
            case "REG":
                reg_name = dest[2:] if dest.startswith('0r') else dest
                self.registres[reg_name] = to_8bits(valeur)
            case "RAM":
                self.ram[int(dest, 16)] = to_8bits(valeur)
            case "DISK":
                self.disk[int(dest, 16)] = to_8bits(valeur)
            case _:
                raise ValueError(f"Destination invalide mov: {dest}")

    def set(self, dest, src):
        src_type = self.detect_type(src)
        match src_type:
            case "INT":
                valeur = to_8bits(int(src))
            case "STR":
                valeur = to_8bits(ord(str(src)[0]))
            case _:
                raise ValueError(f"Entrée invalide set: {src}")

        dest_type = self.detect_type(dest)
        match dest_type:
            case "REG":
                reg_name = dest[2:] if dest.startswith('0r') else dest
                self.registres[reg_name] = to_8bits(valeur)
            case "RAM":
                self.ram[int(dest, 16)] = to_8bits(valeur)
            case "DISK":
                self.disk[int(dest, 16)] = to_8bits(valeur)
            case _:
                raise ValueError(f"Destination invalide set: {dest}")

    def waitkey(self):
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
        self.rip = 0
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
                    case 'setbuffer':
                        self.setbuffer(args[0])
                    case 'addbuffer':
                        self.addbuffer(*args)
                    case 'stdout':
                        self.stdout(args[0])
                    case 'stdoutflush':
                        self.stdout_renderer.buffer = ""
                    case 'jmp':
                        if args[0] not in self.etiquettes:
                            raise ValueError(f.error + f"Étiquette inconnue '{args[0]}' pour jmp.")
                        self.rip = self.etiquettes[args[0]]
                        continue
                    case 'call':
                        if args[0] not in self.etiquettes:
                            raise ValueError(f.error + f"Étiquette inconnue '{args[0]}' pour call.")
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
                        if not self.pile:
                            self.rip = len(self.programme)
                        else:
                            self.rip = self.pile.pop()
                        continue
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
        if 0 < self.rip <= len(self.programme):
            last_instr = self.programme[self.rip-1]
        else:
            last_instr = 'N/A'
        print(f.info + f"Program ended at RIP: {self.rip} ( instruction {last_instr})")
        print("\n=== Registres : ===")
        for registre, valeur in self.registres.items():
            print(f.success + f"{registre}: {valeur}")
        print("\n=== Buffers : ===")
        for buffer, valeur in self.buffers.items():
            texte = ''.join(chr(v) for v in valeur if v != 0)
            print(f.success + f"{buffer}: {texte!r} (codes: {valeur})")
        print("\n=== Informations de débogage ===")
        for info in self.debug_info[:10]:
            print(f.success + info.strip())
        print(f.info + f"Les instructions complètes sont disponibles dans le fichier 'logs_execution.txt'.")

if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Machine Virtuelle avec Pygame")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24)

    programme = """
    setbuffer 0bprompt
    startvm:
    call start_line
    call save_key
    call show_buffer_keys
    jmp startvm

    start_line:
    stdoutflush
    stdout 36    ; $
    stdout 115   ; s
    stdout 104   ; h
    stdout 101   ; e
    stdout 108   ; l
    stdout 108   ; l
    stdout 58    ; :
    stdout 32    ;  
    stdout 0bprompt    ; afficher le buffer 0bprompt
    ret

    save_key:
    waitkey      ; <-- Attend une touche
    addbuffer 0bprompt 0rclavier    ; ajoute la touche dans le buffer 0bprompt
    ret

    show_buffer_keys:
    stdout 0bprompt
    ret
    """
    cpu = CPU(screen, font)
    cpu.charger_programme(programme)
    cpu.executer()
    cpu.afficher_etat()
    pygame.quit()
