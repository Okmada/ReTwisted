import tkinter as tk


class ScrollFrame(tk.Frame):
    def __init__(self, master, *args, **kw) -> None:
        tk.Frame.__init__(self, master, *args, **kw)
        canvas = tk.Canvas(self)

        scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(fill=tk.BOTH, expand=True)

        self.update()

        self.interior = tk.Frame(canvas)
        self.interior.bind("<Configure>", lambda _, canvas=canvas: canvas.configure(scrollregion=canvas.bbox("all")))

        window_id = canvas.create_window((0, 0), window=self.interior, anchor=tk.NW, width=canvas.winfo_width()-2)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(window_id, width=e.width-2))
