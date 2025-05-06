import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
import re


class CodeEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Éditeur de Code - Langage personnalisé")
        
        # Ajustement de la taille de la fenêtre
        self.root.geometry("1000x600")  # Largeur x Hauteur élargie pour inclure le volet de fonctions

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

        # Cadre principal
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)

        # Zone de texte
        self.text = tk.Text(self.main_frame, wrap="none", undo=True)
        self.text.pack(side="left", fill="both", expand=True)
        self.text.bind("<KeyRelease>", self.on_text_change)

        # Ajouter un raccourci clavier pour "Ctrl+S"
        self.root.bind("<Control-s>", lambda event: self.save_file())

        # Barre de défilement
        self.scroll_y = tk.Scrollbar(self.text, orient="vertical", command=self.text.yview)
        self.scroll_y.pack(side="right", fill="y")
        self.text["yscrollcommand"] = self.scroll_y.set

        # Volet pour afficher les fonctions
        self.function_listbox = tk.Listbox(self.main_frame, width=30)
        self.function_listbox.pack(side="right", fill="y")
        self.function_listbox.bind("<<ListboxSelect>>", self.go_to_function)

        # Fichier actuel
        self.current_file = None

        # Couleurs personnalisées
        self.colors = {
            "instruction": "blue",  # Instructions comme 'mov', 'call', etc.
            "address": "green",     # Adresses mémoire comme '0x10'
            "number": "red",        # Nombres comme '5'
            "string": "orange",        # strings
            "function": "purple"    # Noms de fonctions comme 'nomdefonction:'
        }

        # Configurer la balise de surlignement
        self.text.tag_configure("highlight", background="yellow")

    def new_file(self):
        self.text.delete(1.0, tk.END)
        self.current_file = None
        self.update_function_list()

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Fichiers Texte", "*.txt"), ("Tous les fichiers", "*.*")])
        if file_path:
            with open(file_path, "r") as f:
                content = f.read()
            self.text.delete(1.0, tk.END)
            self.text.insert(1.0, content)
            self.current_file = file_path
            self.update_function_list()

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
            "string": r"""(['"])(?:(?=(\\?))\2.)*?\1"""
,                         # strings
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

    def update_function_list(self):
        """Met à jour la liste des fonctions affichées dans le volet."""
        self.function_listbox.delete(0, tk.END)  # Vider la liste existante
        code = self.text.get(1.0, tk.END)

        # Rechercher les noms de fonctions
        functions = re.finditer(r"^\s*(\w+):", code, re.MULTILINE)
        for func in functions:
            name = func.group(1)
            tk_index = self.text.search(f"{name}:", "1.0", stopindex=tk.END, regexp=True)
            if tk_index:
                line = tk_index.split(".")[0]  # Ligne où se trouve la fonction
                self.function_listbox.insert(tk.END, f"{name} (Ligne {line})")

    def go_to_function(self, event):
        """Se déplacer à la ligne où est définie la fonction sélectionnée et la surligner."""
        # Supprimer les anciens surlignements
        self.text.tag_remove("highlight", "1.0", tk.END)

        selected = self.function_listbox.curselection()
        if selected:
            function_text = self.function_listbox.get(selected[0])
            function_name = function_text.split(" ")[0]  # Extraire le nom de la fonction
            tk_index = self.text.search(f"{function_name}:", "1.0", stopindex=tk.END, regexp=True)
            if tk_index:
                # Faire défiler jusqu'à la ligne
                self.text.see(tk_index)
                self.text.mark_set("insert", tk_index)

                # Surligner la ligne
                line_start = f"{tk_index.split('.')[0]}.0"  # Début de la ligne
                line_end = f"{int(tk_index.split('.')[0]) + 1}.0"  # Début de la ligne suivante
                self.text.tag_add("highlight", line_start, line_end)

    def on_text_change(self, event=None):
        """Met à jour la liste des fonctions, la coloration syntaxique et supprime les surlignements après modification du texte."""
        self.syntax_highlight()
        self.update_function_list()
        self.text.tag_remove("highlight", "1.0", tk.END)


if __name__ == "__main__":
    root = tk.Tk()
    editor = CodeEditor(root)
    root.mainloop()
