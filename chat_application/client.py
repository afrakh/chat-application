import socket
import threading
import tkinter as tk
from tkinter import simpledialog, scrolledtext, messagebox
from PIL import Image, ImageDraw, ImageFont, ImageTk
from datetime import datetime
import queue
import sys


HOST_DEFAULT = '127.0.0.1'
PORT_DEFAULT = 55000

class ChatClientGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Chat Client (GUI)")
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)


        top_frame = tk.Frame(master)
        top_frame.pack(padx=8, pady=4, fill="x")

        tk.Label(top_frame, text="Server IP:").pack(side="left")
        self.ip_entry = tk.Entry(top_frame, width=14)
        self.ip_entry.pack(side="left", padx=(2,10))
        self.ip_entry.insert(0, HOST_DEFAULT)

        tk.Label(top_frame, text="Port:").pack(side="left")
        self.port_entry = tk.Entry(top_frame, width=6)
        self.port_entry.pack(side="left", padx=(2,10))
        self.port_entry.insert(0, str(PORT_DEFAULT))

        self.connect_btn = tk.Button(top_frame, text="Connect", command=self.try_connect)
        self.connect_btn.pack(side="right")


        chat_canvas = tk.Canvas(master, bg="#f5f5f5", highlightthickness=0)
        chat_scrollbar = tk.Scrollbar(master, orient="vertical", command=chat_canvas.yview)
        self.chat_frame = tk.Frame(chat_canvas, bg="#f5f5f5")

        self.chat_frame.bind(
        "<Configure>",
        lambda e: chat_canvas.configure(scrollregion=chat_canvas.bbox("all"))
        )

        chat_canvas.create_window((0, 0), window=self.chat_frame, anchor="nw")
        chat_canvas.configure(yscrollcommand=chat_scrollbar.set)

        chat_canvas.pack(side="left", fill="both", expand=True, padx=8, pady=(4, 0))
        chat_scrollbar.pack(side="right", fill="y")

        self.chat_canvas = chat_canvas
        self.chat_scrollbar = chat_scrollbar

        
        
    
        
        bottom_frame = tk.Frame(master)
        bottom_frame.pack(padx=8, pady=6, fill="x")

        self.msg_entry = tk.Entry(bottom_frame, width=48)
        self.msg_entry.pack(side="left", padx=(0,6), fill="x", expand=True)
        self.msg_entry.bind("<Return>", lambda event: self.send_message())
        self.msg_entry.bind("<KeyRelease>", lambda e: self.notify_typing())

        self.emoji_btn = tk.Button(bottom_frame, text="😊", font=("Segoe UI Emoji", 12), command=self.open_emoji_picker)
        self.emoji_btn.pack(side="left", padx=(0, 5))



        self.send_btn = tk.Button(bottom_frame, text="Send", command=self.send_message, state='disabled')
        self.send_btn.pack(side="left")

        
        self.socket = None
        self.receive_thread = None
        self.running = False

        
        self.msg_queue = queue.Queue()

        
        self.nickname = simpledialog.askstring("Nickname", "Choose a nickname:", parent=self.master)
        if not self.nickname:
            messagebox.showinfo("Cancelled", "No nickname chosen. Exiting.")
            self.master.after(100, self.master.destroy)

        
        self.master.after(100, self.process_queue)

        self.user_statuses = {}  

    
    def notify_typing(self):
        if self.socket and self.running:
            try:
                self.socket.send(f"TYPING:{self.nickname}".encode("utf-8"))
            except:
                pass


    def try_connect(self):
        ip = self.ip_entry.get().strip() or HOST_DEFAULT
        try:
            port = int(self.port_entry.get().strip())
        except ValueError:
            messagebox.showerror("Invalid Port", "Please enter a valid port number.")
            return


        self.connect_btn.config(state='disabled')
        self.ip_entry.config(state='disabled')
        self.port_entry.config(state='disabled')


        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((ip, port))
        except Exception as e:
            messagebox.showerror("Connection Failed", f"Could not connect to {ip}:{port}\n{e}")
            
            self.connect_btn.config(state='normal')
            self.ip_entry.config(state='normal')
            self.port_entry.config(state='normal')
            return

        self.running = True
        self.send_btn.config(state='normal')
        self.append_message(f"Connected to server {ip}:{port}")

        
        self.receive_thread = threading.Thread(target=self.receive_loop, daemon=True)
        self.receive_thread.start()

    def receive_loop(self):
        try:
            while self.running:
                try:
                    data = self.socket.recv(1024)
                except OSError:
                    break
                if not data:
                    break
                message = data.decode('utf-8')

                
                if message == 'NICK':
                    try:
                        self.socket.send(self.nickname.encode('utf-8'))
                    except Exception:
                        break

                
                elif message.startswith("TYPING_EVENT:"):
                    typer = message.split(":", 1)[1]
                    if typer != self.nickname:  
                        self.master.after(0, lambda: self.show_typing_indicator(typer))
                    continue  

                else:
                    self.msg_queue.put(message)


        except Exception as e:
            self.msg_queue.put(f"[Error receiving]: {e}")
        finally:
            self.running = False
            self.msg_queue.put("[Disconnected from server]")


    def send_message(self):
        if not self.socket or not self.running:
            messagebox.showwarning("Not connected", "Connect to a server first.")
            return
        text = self.msg_entry.get().strip()
        if not text:
            return
        full_msg = f"{self.nickname}: {text}"
        try:
            self.socket.send(full_msg.encode('utf-8'))
        except Exception as e:
            messagebox.showerror("Send failed", f"Could not send message: {e}")
            self.socket.close()
            self.running = False
            return
        self.msg_entry.delete(0, tk.END)

    def append_message(self, message):
        bubble_frame = tk.Frame(self.chat_frame, bg="#f5f5f5")
        bubble_frame.pack(fill="x", pady=3, padx=10)


        if message.startswith(f"{self.nickname}:"):

            sender = "self"
            msg = message.split(":", 1)[1].strip()
            bg_color = "#dcf8c6"   
            text_color = "black"
            anchor = "e"
        elif any(x in message for x in ["joined the chat", "left the chat", "Connected to server"]):

            sender = "system"
        else:

            sender = "other"
            msg = message
            bg_color = "#ffffff"  
            text_color = "black"
            anchor = "w"

    
        if sender == "system":
            label = tk.Label(
                bubble_frame,
                text=message,
                fg="gray",
                font=("Segoe UI", 9, "italic"),
                bg="#f5f5f5"
            )
            label.pack(anchor="center")
            return
        
        timestamp = datetime.now().strftime("%I:%M %p")

        
        font = ImageFont.truetype("seguiemj.ttf", 13)
        time_font = ImageFont.truetype("seguiemj.ttf", 9)
        padding_x, padding_y = 14, 8


        dummy_img = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(dummy_img)

  
        try:
            bbox = font.getbbox(msg)
        except AttributeError:
            bbox = draw.textbbox((0, 0), msg, font=font)

        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        try:
            time_bbox = time_font.getbbox(timestamp)
        except AttributeError:
            time_bbox = draw.textbbox((0, 0), timestamp, font=time_font)
        time_width = time_bbox[2] - time_bbox[0]
        time_height = time_bbox[3] - time_bbox[1]

        bubble_width = max(text_width + 2 * padding_x, time_width + 2 * padding_x)
        bubble_height = text_height + time_height + 3 * padding_y



        
        bubble_img = Image.new("RGBA", (bubble_width, bubble_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(bubble_img)
        radius = 15
        draw.rounded_rectangle(
            [(0, 0), (bubble_width, bubble_height)],
            radius=radius,
            fill=bg_color
        )

        
        draw.text((padding_x, padding_y), msg, fill=text_color, font=font)
        draw.text(
        (bubble_width - time_width - 10, bubble_height - time_height - 5),
        timestamp,
        fill="gray",
        font=time_font
    )
        
        bubble_tk = ImageTk.PhotoImage(bubble_img)

        
        label = tk.Label(bubble_frame, image=bubble_tk, bg="#f5f5f5", bd=0)
        label.image = bubble_tk
        label.pack(anchor=anchor, padx=10, pady=2)

        self.chat_canvas.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)



       
   

    def process_queue(self):
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                self.append_message(msg)
        except queue.Empty:
            pass
        if self.running:
            self.master.after(100, self.process_queue)
        else:
            self.master.after(500, self.process_queue)


    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.running = False
            try:
                if self.socket:
                    self.socket.close()
            except:
                pass
            self.master.destroy()

    def show_typing_indicator(self, name):
        if hasattr(self, "typing_label"):
            self.typing_label.destroy()  

        self.typing_label = tk.Label(
        self.master,
        text=f"💬  {name} is typing...",
        fg="white",
        bg="#25D366", 
        font=("Segoe UI", 10, "bold"),
        padx=10,
        pady=4,
        relief="ridge",
        bd=2
    )
        self.typing_label.place(relx=0.5, rely=0.95, anchor="center")
        self.master.after(3000, self.hide_typing_indicator)

    def hide_typing_indicator(self):
        if hasattr(self, "typing_label"):
            self.typing_label.destroy()
            del self.typing_label

    def open_emoji_picker(self):
        if hasattr(self, "emoji_window") and self.emoji_window.winfo_exists():
            self.emoji_window.destroy()
            return

        self.emoji_window = tk.Toplevel(self.master)
        self.emoji_window.title("Emoji Picker")
        self.emoji_window.geometry("340x300")
        self.emoji_window.config(bg="#ffffff")
        self.emoji_window.resizable(False, False)
        self.emoji_window.attributes('-topmost', True)

        
        container = tk.Frame(self.emoji_window, bg="white")
        container.pack(fill="both", expand=True)

        
        canvas = tk.Canvas(container, bg="white", highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="white")

        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        
        emojis = [
            "😀","😁","😂","🤣","😃","😄","😅","😆","😉","😊","😋","😎","😍","😘","😗","😙","😚",
            "🙂","🤗","🤩","🤔","🤨","😐","😑","😶","🙄","😏","😣","😥","😮","🤐","😯","😪",
            "😫","😴","😌","🤓","😛","😜","🤪","😝","🤑","🤠","😒","😓","😔","😕","🙃","🫠",
            "🫡","😲","☹️","🙁","😖","😞","😟","😤","😢","😭","😦","😧","😨","😩","🤯","😬",
            "😰","😱","🥵","🥶","😳","🤪","😵","🤕","🤢","🤮","🤧","🥲","🤠","😇","🥰","🤫",
            "😷","🤭","🤔","🤗","🫶","❤️","🩷","💔","💖","💙","💜","💚","🧡","🤍","🖤","💛","💞","💫","✨"
        ]

        row = 0
        col = 0
        for emo in emojis:
            btn = tk.Button(
                scrollable_frame,
                text=emo,
                font=("Segoe UI Emoji", 14),
                relief="flat",
                bg="white",
                activebackground="#e6f7ff",
                command=lambda e=emo: self.insert_emoji(e)
            )
            btn.grid(row=row, column=col, padx=3, pady=3)
            col += 1
            if col == 8:
                col = 0
                row += 1

        
        def _on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except tk.TclError:

                pass

        canvas.bind_all("<MouseWheel>", _on_mousewheel)


        def on_close_emoji():
            try:
                canvas.unbind_all("<MouseWheel>")
            except Exception:
                pass
            self.emoji_window.destroy()

        self.emoji_window.protocol("WM_DELETE_WINDOW", on_close_emoji)


    def insert_emoji(self, emoji_char):
        self.msg_entry.insert(tk.END, emoji_char)
        self.emoji_window.destroy()


    def update_status(self, name, status):
        if name == self.nickname:
            return  

        self.user_statuses[name] = status

        if not hasattr(self, "status_frame"):
            self.status_frame = tk.Frame(self.master, bg="#f5f5f5")
            self.status_frame.pack(side="top", pady=(4, 2), fill="x")


        for widget in self.status_frame.winfo_children():
            widget.destroy()


        for uname, stat in self.user_statuses.items():
            color = "green" if stat == "online" else "red"
            symbol = "🟢" if stat == "online" else "🔴"

            lbl = tk.Label(
                self.status_frame,
                text=f"{uname} ({symbol} {stat.capitalize()})",
                fg=color,
                font=("Segoe UI", 10, "italic"),
                bg="#f5f5f5",
                anchor="w"
            )
            lbl.pack(side="left", padx=8)
    



if __name__ == "__main__":
    root = tk.Tk()
    app = ChatClientGUI(root)
    root.mainloop()
