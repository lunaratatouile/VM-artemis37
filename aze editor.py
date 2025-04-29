import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
import re


class CodeEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Éditeur de Code - Langage personnalisé")
        
        # Ajustement de la taille de la fenêtre
        self.root.geometry("800x600")  # Largeur x Hauteur

        # Barre de menus
        self.menu = tk.Menu(self.root)
        self.root.config(menu=self.menu)
        self.file_menu = tk.Menu(self.menu, tearoff=0)
        self.file_menu.add_command(label="Nouveau", command=self.new_file)
        self.file_menu.add_command(label="Ouvrir...", command=self.open_file)
        self.file_menu.add_command(label="Enregistrer", command=self.save_file)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Quitter", command=self.root.quit)
        self.menu.add_cascade(label="Fichier", menu=self.file_menu)

        # Zone de texte
        self.text = tk.Text(self.root, wrap="none", undo=True)
        self.text.pack(fill="both", expand=True)
        self.text.bind("<KeyRelease>", self.syntax_highlight)

        # Ajouter un raccourci clavier pour "Ctrl+S"
        self.root.bind("<Control-s>", lambda event: self.save_file())

        # Barre de défilement
        self.scroll_y = tk.Scrollbar(self.text, orient="vertical", command=self.text.yview)
        self.scroll_y.pack(side="right", fill="y")
        self.text["yscrollcommand"] = self.scroll_y.set

        # Fichier actuel
        self.current_file = None

        # Couleurs personnalisées
        self.colors = {
            "instruction": "blue",  # Instructions comme 'mov', 'call', etc.
            "address": "green",     # Adresses mémoire comme '0x10'
            "number": "red",        # Nombres comme '5'
            "function": "purple"    # Noms de fonctions comme 'nomdefonction:'
        }

    def new_file(self):
        self.text.delete(1.0, tk.END)
        self.current_file = None

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Fichiers Texte", "*.txt"), ("Tous les fichiers", "*.*")])
        if file_path:
            with open(file_path, "r") as f:
                content = f.read()
            self.text.delete(1.0, tk.END)
            self.text.insert(1.0, content)
            self.current_file = file_path

    def save_file(self):
        if self.current_file:
            with open(self.current_file, "w") as f:
                f.write(self.text.get(1.0, tk.END))
            messagebox.showinfo("Enregistrement", "Fichier enregistré avec succès.")
        else:
            file_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                                     filetypes=[("Fichiers Texte", "*.txt"), ("Tous les fichiers", "*.*")])
            if file_path:
                with open(file_path, "w") as f:
                    f.write(self.text.get(1.0, tk.END))
                self.current_file = file_path
                messagebox.showinfo("Enregistrement", "Fichier enregistré avec succès.")

    def syntax_highlight(self, event=None):
        """Ajoute des couleurs pour la syntaxe définie par l'utilisateur."""
        code = self.text.get(1.0, tk.END)
        
        # Supprimer les anciennes balises
        for tag in self.text.tag_names():
            self.text.tag_remove(tag, "1.0", tk.END)

        # Définitions des expressions régulières
        patterns = {
            "instruction": r"\b(mov|jmp|call|ret|xor)\b",  # Instructions
            "address": r"\b0x[0-9a-fA-F]+\b",             # Adresses mémoire
            "number": r"\b\d+\b",                         # Nombres (entiers)
            "function": r"\b\w+:\b"                       # Noms de fonctions suivis de ':'
        }

        # Appliquer les couleurs
        for token_type, pattern in patterns.items():
            for match in re.finditer(pattern, code):
                start_index = f"1.0 + {match.start()}c"
                end_index = f"1.0 + {match.end()}c"
                self.text.tag_add(token_type, start_index, end_index)

        # Configurer les couleurs
        for token_type, color in self.colors.items():
            self.text.tag_configure(token_type, foreground=color)


if __name__ == "__main__":
    root = tk.Tk()
    editor = CodeEditor(root)
    root.mainloop()
