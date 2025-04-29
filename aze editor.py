import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from pygments import lex
from pygments.lexers import PythonLexer
from pygments.token import Token


class CodeEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Éditeur de Code - Langage personnalisé")

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

        # Barre de défilement
        self.scroll_y = tk.Scrollbar(self.text, orient="vertical", command=self.text.yview)
        self.scroll_y.pack(side="right", fill="y")
        self.text["yscrollcommand"] = self.scroll_y.set

        # Fichier actuel
        self.current_file = None

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
        else:
            file_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                                     filetypes=[("Fichiers Texte", "*.txt"), ("Tous les fichiers", "*.*")])
            if file_path:
                with open(file_path, "w") as f:
                    f.write(self.text.get(1.0, tk.END))
                self.current_file = file_path

    def syntax_highlight(self, event=None):
        """Ajoute des couleurs pour la syntaxe."""
        code = self.text.get(1.0, tk.END)
        self.text.mark_set("range_start", "1.0")
        data = lex(code, PythonLexer())
        for token, content in data:
            self.text.mark_set("range_end", "range_start + %dc" % len(content))
            self.text.tag_add(str(token), "range_start", "range_end")
            self.text.mark_set("range_start", "range_end")

        # Définir les couleurs
        self.text.tag_configure(Token.Keyword, foreground="blue")  # Mots-clés
        self.text.tag_configure(Token.Literal.Number, foreground="red")  # Nombres
        self.text.tag_configure(Token.Operator, foreground="purple")  # Opérateurs
        self.text.tag_configure(Token.Text, foreground="black")  # Texte normal


if __name__ == "__main__":
    root = tk.Tk()
    editor = CodeEditor(root)
    root.mainloop()
