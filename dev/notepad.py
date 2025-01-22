import tkinter as tk
from tkinter import ttk, colorchooser
from PIL import ImageGrab, Image, ImageTk


class PaintApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Notepad")
        self.current_tool = "line"
        self.start_x = None
        self.start_y = None
        self.preview_item = None
        self.current_color = "black"
        self.current_line = None
        self.history = []
        self.create_tool_selector()
        self.create_canvas()
        self.bind_shortcuts()


    def create_tool_selector(self):
        tool_frame = ttk.Frame(self.root)
        tool_frame.pack(side=tk.TOP, fill=tk.X)
        tools = []
        tools.append(ttk.Button(tool_frame, text="Clear", command=self.clear_canvas))
        tools.append(ttk.Button(tool_frame, text="Eraser", command=lambda: self.set_tool("eraser")))
        tools.append(ttk.Button(tool_frame, text="Pencil", command=lambda: self.set_tool("pencil")))
        tools.append(ttk.Button(tool_frame, text="Line", command=lambda: self.set_tool("line")))
        tools.append(ttk.Button(tool_frame, text="Circle", command=lambda: self.set_tool("circle")))
        tools.append(ttk.Button(tool_frame, text="Rectangle", command=lambda: self.set_tool("rectangle")))
        tools.append(ttk.Button(tool_frame, text="Color Picker", command=self.choose_color))
        tools.append(ttk.Button(tool_frame, text="Text", command=lambda: self.set_tool("text")))
        self.text_entry = ttk.Entry(tool_frame, width=20)
        tools.append(self.text_entry)
        self.text_size = ttk.Spinbox(tool_frame, from_=8, to=72, width=4)
        self.text_size.set(12)
        tools.append(self.text_size)
        self.line_width = ttk.Spinbox(tool_frame, from_=1, to=12, width=4)
        self.line_width.set(1)
        tools.append(self.line_width)
        for tool in tools:
            tool.pack(side=tk.LEFT, padx=2, pady=5)


    def create_canvas(self):
        self.canvas = tk.Canvas(self.root, bg="white", width=1000, height=800)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.preview_draw)
        self.canvas.bind("<ButtonRelease-1>", self.end_draw)


    def bind_shortcuts(self):
        self.root.bind("<Control-z>", self.undo)
        self.root.bind("<Control-v>", self.paste_image)


    def clear_canvas(self):
        self.canvas.delete("all")
        self.history.clear()


    def set_tool(self, tool):
        self.current_tool = tool


    def choose_color(self):
        color_code = colorchooser.askcolor(title="Choose color")[1]
        if color_code:
            self.current_color = color_code


    def start_draw(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.preview_item = None
        self.current_line = None


    def preview_draw(self, event):
        if self.preview_item:
            self.canvas.delete(self.preview_item)

        if self.current_tool == "eraser":
            self.preview_item = self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline="gray", dash=(2, 2))

        elif self.current_tool == "pencil":
            if self.current_line is None:
                line_width = int(self.line_width.get())
                self.current_line = self.canvas.create_line(event.x, event.y, event.x, event.y, width=line_width, fill=self.current_color)
            self.canvas.coords(self.current_line, *self.canvas.coords(self.current_line), event.x, event.y)

        elif self.current_tool == "line":
            self.preview_item = self.canvas.create_line(self.start_x, self.start_y, event.x, event.y, fill="gray", dash=(2, 2))

        elif self.current_tool == "circle":
            radius = ((event.x - self.start_x) ** 2 + (event.y - self.start_y) ** 2) ** 0.5
            x = self.start_x - radius, self.start_y - radius
            y = self.start_x + radius, self.start_y + radius
            self.preview_item = self.canvas.create_oval(x, y, outline="gray", dash=(2, 2))

        elif self.current_tool == "rectangle":
            self.preview_item = self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, outline="gray", dash=(2, 2))

        elif self.current_tool == "text":
            text = self.text_entry.get()
            size = int(self.text_size.get())
            self.preview_item = self.canvas.create_text(event.x, event.y, text=text, font=("Arial", size), fill=self.current_color)


    def end_draw(self, event):
        if self.preview_item:
            self.canvas.delete(self.preview_item)

        item = None

        if self.current_tool == "eraser":
            item = self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, fill="white", outline="white")

        elif self.current_tool == "pencil":
            if self.current_line:
                item = self.current_line

        elif self.current_tool == "line":
            line_width = int(self.line_width.get())
            item = self.canvas.create_line(self.start_x, self.start_y, event.x, event.y, width=line_width, fill=self.current_color)

        elif self.current_tool == "circle":
            radius = ((event.x - self.start_x) ** 2 + (event.y - self.start_y) ** 2) ** 0.5
            x = self.start_x - radius, self.start_y - radius
            y = self.start_x + radius, self.start_y + radius
            line_width = int(self.line_width.get())
            item = self.canvas.create_oval(x, y, width=line_width, outline=self.current_color)

        elif self.current_tool == "rectangle":
            line_width = int(self.line_width.get())
            item = self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, width=line_width, outline=self.current_color)

        elif self.current_tool == "text":
            text = self.text_entry.get()
            size = int(self.text_size.get())
            item = self.canvas.create_text(event.x, event.y, text=text, font=("Arial", size), fill=self.current_color)

        if item:
            self.history.append(item)

        self.start_x = None
        self.start_y = None


    def undo(self, event=None):
        if self.history:
            last_item = self.history.pop()
            self.canvas.delete(last_item)


    def paste_image(self, event=None):
        try:
            clipboard_image = ImageGrab.grabclipboard()
            if isinstance(clipboard_image, Image.Image):
                image_tk = ImageTk.PhotoImage(clipboard_image)
                x, y = self.canvas.winfo_pointerx() - self.canvas.winfo_rootx(), self.canvas.winfo_pointery() - self.canvas.winfo_rooty()
                image_id = self.canvas.create_image(x, y, anchor=tk.NW, image=image_tk)
                self.history.append(image_id)
                self.canvas.image_tk = image_tk
            else:
                print("No image found on the clipboard.")
        except Exception as e:
            print(f"Error pasting image: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = PaintApp(root)
    root.mainloop()
