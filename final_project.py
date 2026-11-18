import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox, ttk
import cv2
import numpy as np
from PIL import Image, ImageTk
from collections import deque
import copy


class FloodFillApp:
    def __init__(self, root):
        self.root = root
        self.root.title("تطبيق تلوين الصور - Flood Fill")
        self.root.geometry("1100x750")
        self.root.configure(bg="#1e1e2e")
        self.root.resizable(True, True)

        
        self.original_image = None       
        self.display_image = None        
        self.history = []                
        self.selected_color = (255, 0, 0)   
        self.tolerance = 20
        self.zoom_factor = 1.0
        self.canvas_offset_x = 0
        self.canvas_offset_y = 0
        self.is_cropping = False
        self.crop_start = None
        self.crop_rect = None
        self.mode = "fill"   

        self._build_ui()

    
    
    def _build_ui(self):
        
        toolbar = tk.Frame(self.root, bg="#313244", height=55, relief="flat")
        toolbar.pack(fill="x", side="top")
        toolbar.pack_propagate(False)

        btn_style = {"bg": "#89b4fa", "fg": "#1e1e2e", "font": ("Arial", 10, "bold"),
                    "relief": "flat", "padx": 12, "pady": 6, "cursor": "hand2",
                    "activebackground": "#74c7ec", "activeforeground": "#1e1e2e", "bd": 0}

        tk.Button(toolbar, text="📂 فتح صورة", command=self.open_image, **btn_style).pack(side="left", padx=(10, 4), pady=8)
        tk.Button(toolbar, text="💾 حفظ الصورة", command=self.save_image, **btn_style).pack(side="left", padx=4, pady=8)
        tk.Button(toolbar, text="↩ تراجع (Undo)", command=self.undo, **btn_style).pack(side="left", padx=4, pady=8)

        tk.Label(toolbar, text="  |  ", bg="#313244", fg="#6c7086").pack(side="left")

        
        self.mode_fill_btn = tk.Button(toolbar, text="🖌 تلوين", command=lambda: self.set_mode("fill"),
                                    bg="#a6e3a1", fg="#1e1e2e", font=("Arial", 10, "bold"),
                                    relief="flat", padx=12, pady=6, cursor="hand2", bd=0)
        self.mode_fill_btn.pack(side="left", padx=4, pady=8)

        self.mode_crop_btn = tk.Button(toolbar, text="✂ قص", command=lambda: self.set_mode("crop"),
                                    bg="#313244", fg="#cdd6f4", font=("Arial", 10, "bold"),
                                    relief="flat", padx=12, pady=6, cursor="hand2", bd=0)
        self.mode_crop_btn.pack(side="left", padx=4, pady=8)

        tk.Label(toolbar, text="  |  ", bg="#313244", fg="#6c7086").pack(side="left")

        
        self.color_preview = tk.Label(toolbar, bg="#ff0000", width=4, relief="flat", cursor="hand2")
        self.color_preview.pack(side="left", padx=(4, 2), pady=12)
        self.color_preview.bind("<Button-1>", lambda e: self.pick_color())
        tk.Button(toolbar, text="🎨 اختر لون", command=self.pick_color, **btn_style).pack(side="left", padx=(0, 4), pady=8)

        
        tk.Label(toolbar, text="  التفاوت:", bg="#313244", fg="#cdd6f4",
                font=("Arial", 10)).pack(side="left", padx=(8, 2))
        self.tolerance_var = tk.IntVar(value=20)
        tol_slider = tk.Scale(toolbar, from_=0, to=100, orient="horizontal",
                            variable=self.tolerance_var, bg="#313244", fg="#cdd6f4",
                            troughcolor="#45475a", highlightthickness=0, length=120,
                            command=self._on_tolerance_change)
        tol_slider.pack(side="left", pady=8)

        
        tk.Label(toolbar, text="  تكبير:", bg="#313244", fg="#cdd6f4",
                font=("Arial", 10)).pack(side="left", padx=(8, 2))
        self.zoom_var = tk.DoubleVar(value=1.0)
        zoom_slider = tk.Scale(toolbar, from_=0.2, to=3.0, resolution=0.1, orient="horizontal",
                            variable=self.zoom_var, bg="#313244", fg="#cdd6f4",
                            troughcolor="#45475a", highlightthickness=0, length=100,
                            command=self._on_zoom_change)
        zoom_slider.pack(side="left", pady=8)

        
        main_frame = tk.Frame(self.root, bg="#1e1e2e")
        main_frame.pack(fill="both", expand=True)

        
        canvas_frame = tk.Frame(main_frame, bg="#1e1e2e")
        canvas_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(canvas_frame, bg="#181825", cursor="crosshair",
                                highlightthickness=1, highlightbackground="#45475a")
        self.canvas.grid(row=0, column=0, sticky="nsew")

        v_scroll = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
        h_scroll.grid(row=1, column=0, sticky="ew")

        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.columnconfigure(0, weight=1)

        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)

        
        self.welcome_label = tk.Label(self.canvas, text="📂  افتح صورة للبدء",
                                    bg="#181825", fg="#6c7086",
                                    font=("Arial", 18))
        self.canvas.create_window(400, 300, window=self.welcome_label)

        
        self.status_var = tk.StringVar(value="جاهز | افتح صورة للبدء")
        status_bar = tk.Label(self.root, textvariable=self.status_var,
                            bg="#313244", fg="#a6adc8", font=("Arial", 9),
                            anchor="w", padx=10)
        status_bar.pack(fill="x", side="bottom")

    
    def set_mode(self, mode):
        self.mode = mode
        if mode == "fill":
            self.canvas.configure(cursor="crosshair")
            self.mode_fill_btn.configure(bg="#a6e3a1", fg="#1e1e2e")
            self.mode_crop_btn.configure(bg="#313244", fg="#cdd6f4")
            self.status_var.set("وضع التلوين: انقر على منطقة في الصورة لتلوينها")
        else:
            self.canvas.configure(cursor="plus")
            self.mode_fill_btn.configure(bg="#313244", fg="#cdd6f4")
            self.mode_crop_btn.configure(bg="#fab387", fg="#1e1e2e")
            self.status_var.set("وضع القص: ارسم مستطيلاً لتحديد المنطقة المراد قصها")

    def pick_color(self):
        
        color = colorchooser.askcolor(title="اختر اللون", parent=self.root)
        if color and color[0]:
            r, g, b = [int(c) for c in color[0]]
            self.selected_color = (b, g, r)   # BGR for OpenCV
            self.color_preview.configure(bg=color[1])
            self.status_var.set(f"تم اختيار اللون: RGB({r},{g},{b})")

    def _on_tolerance_change(self, val):
        self.tolerance = int(float(val))

    def _on_zoom_change(self, val):
        self.zoom_factor = float(val)
        if self.display_image is not None:
            self._render_canvas()

    
    
    def open_image(self):
        path = filedialog.askopenfilename(
            title="اختر صورة",
            filetypes=[("صور", "*.png *.jpg *.jpeg *.bmp *.tiff *.gif"), ("الكل", "*.*")]
        )
        if not path:
            return
        img = cv2.imread(path)
        if img is None:
            messagebox.showerror("خطأ", "تعذّر فتح الصورة. تأكد من صحة الملف.")
            return
        self.original_image = img.copy()
        self.display_image = img.copy()
        self.history.clear()
        self.zoom_var.set(1.0)
        self.zoom_factor = 1.0
        if hasattr(self, 'welcome_label'):
            self.welcome_label.destroy()
            del self.welcome_label
        self._render_canvas()
        h, w = img.shape[:2]
        self.status_var.set(f"تم فتح الصورة: {path.split('/')[-1]}  |  الأبعاد: {w}×{h} بكسل")

    def save_image(self):
        if self.display_image is None:
            messagebox.showwarning("تنبيه", "لا توجد صورة لحفظها.")
            return
        path = filedialog.asksaveasfilename(
            title="حفظ الصورة",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("BMP", "*.bmp")]
        )
        if path:
            cv2.imwrite(path, self.display_image)
            self.status_var.set(f"✅ تم الحفظ: {path.split('/')[-1]}")
            messagebox.showinfo("نجاح", f"تم حفظ الصورة بنجاح:\n{path}")

    
    def _render_canvas(self):
        if self.display_image is None:
            return
        h, w = self.display_image.shape[:2]
        nw = max(1, int(w * self.zoom_factor))
        nh = max(1, int(h * self.zoom_factor))

        resized = cv2.resize(self.display_image, (nw, nh), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        self._tk_image = ImageTk.PhotoImage(pil_img)

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self._tk_image)
        self.canvas.configure(scrollregion=(0, 0, nw, nh))

    def _canvas_to_image_coords(self, cx, cy):
        
        sx = self.canvas.canvasx(cx)
        sy = self.canvas.canvasy(cy)
        ix = int(sx / self.zoom_factor)
        iy = int(sy / self.zoom_factor)
        return ix, iy

    
    
    def on_canvas_click(self, event):
        if self.display_image is None:
            return
        if self.mode == "fill":
            ix, iy = self._canvas_to_image_coords(event.x, event.y)
            self._do_flood_fill(ix, iy)
        elif self.mode == "crop":
            self.crop_start = (event.x, event.y)
            if self.crop_rect:
                self.canvas.delete(self.crop_rect)

    def on_canvas_drag(self, event):
        if self.mode == "crop" and self.crop_start:
            if self.crop_rect:
                self.canvas.delete(self.crop_rect)
            self.crop_rect = self.canvas.create_rectangle(
                self.crop_start[0], self.crop_start[1], event.x, event.y,
                outline="#f38ba8", width=2, dash=(4, 4)
            )

    def on_canvas_release(self, event):
        if self.mode == "crop" and self.crop_start:
            x1, y1 = self._canvas_to_image_coords(*self.crop_start)
            x2, y2 = self._canvas_to_image_coords(event.x, event.y)
            self._do_crop(x1, y1, x2, y2)
            self.crop_start = None

    
    
    def _do_flood_fill(self, x, y):
        
        img = self.display_image
        h, w = img.shape[:2]

        
        if x < 0 or x >= w or y < 0 or y >= h:
            return

        is_gray = (len(img.shape) == 2)
        target_color = img[y, x].copy()

        fill_b, fill_g, fill_r = self.selected_color

        
        if is_gray:
            if abs(int(target_color) - int(fill_b)) <= self.tolerance:
                return
        else:
            if (abs(int(target_color[0]) - fill_b) <= self.tolerance and
                    abs(int(target_color[1]) - fill_g) <= self.tolerance and
                    abs(int(target_color[2]) - fill_r) <= self.tolerance):
                return

        
        self.history.append(self.display_image.copy())
        if len(self.history) > 30:
            self.history.pop(0)

        
        visited = np.zeros((h, w), dtype=bool)
        queue = deque()
        queue.append((x, y))
        visited[y, x] = True

        
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]

        pixels_filled = 0

        while queue:
            cx, cy = queue.popleft()

            
            if is_gray:
                
                orig_lum = int(img[cy, cx])
                target_lum = int(target_color)
                if target_lum > 0:
                    ratio = orig_lum / target_lum
                else:
                    ratio = 1.0
                
                
                avg_fill = (fill_b + fill_g + fill_r) // 3
                new_val = int(min(255, avg_fill * ratio))
                img[cy, cx] = new_val
            else:
                img[cy, cx] = [fill_b, fill_g, fill_r]

            pixels_filled += 1

            
            
            for dx, dy in directions:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < w and 0 <= ny < h and not visited[ny, nx]:
                    neighbor = img[ny, nx]
                    
                    
                    if is_gray:
                        diff = abs(int(neighbor) - int(target_color))
                    else:
                        diff = (abs(int(neighbor[0]) - int(target_color[0])) +
                                abs(int(neighbor[1]) - int(target_color[1])) +
                                abs(int(neighbor[2]) - int(target_color[2])))
                        diff //= 3

                    if diff <= self.tolerance:
                        visited[ny, nx] = True
                        queue.append((nx, ny))

        self._render_canvas()
        self.status_var.set(f"✅ تم تلوين {pixels_filled:,} بكسل | النقطة: ({x},{y}) | التفاوت: {self.tolerance}")

    
    
    def _do_crop(self, x1, y1, x2, y2):
        if self.display_image is None:
            return
        h, w = self.display_image.shape[:2]
        x1 = max(0, min(x1, w - 1))
        x2 = max(0, min(x2, w - 1))
        y1 = max(0, min(y1, h - 1))
        y2 = max(0, min(y2, h - 1))

        if x1 > x2: x1, x2 = x2, x1
        if y1 > y2: y1, y2 = y2, y1

        if x2 - x1 < 5 or y2 - y1 < 5:
            self.status_var.set("المنطقة المحددة صغيرة جداً")
            return

        cropped = self.display_image[y1:y2, x1:x2].copy()

        path = filedialog.asksaveasfilename(
            title="حفظ المنطقة المقصوصة",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")]
        )
        if path:
            cv2.imwrite(path, cropped)
            self.status_var.set(f"✅ تم حفظ المقطع: {(x2-x1)}×{(y2-y1)} بكسل")
            messagebox.showinfo("نجاح", f"تم حفظ المقطع المقصوص:\n{path}")

        if self.crop_rect:
            self.canvas.delete(self.crop_rect)
            self.crop_rect = None


    def undo(self):
        if not self.history:
            messagebox.showinfo("تنبيه", "لا توجد عمليات للتراجع عنها.")
            return
        self.display_image = self.history.pop()
        self._render_canvas()
        self.status_var.set(f"↩ تم التراجع | عدد الخطوات المتبقية: {len(self.history)}")



if __name__ == "__main__":
    root = tk.Tk()
    app = FloodFillApp(root)
    root.mainloop()
