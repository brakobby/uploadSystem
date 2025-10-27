import customtkinter
from tkinter import messagebox
from imported_modules import *
from ui_auth import AuthUI
from ui_dash import DashboardUI
from ui_finance import FinanceUI
from ui_attend import AttendanceUI
from ui_message import MessagingUI
from ui_head_remit import HeadChurchRemitWindow 
import backend
from backend import verify_church, count_all_members, count_male_members, count_female_members
import threading
import time

backend.connect()

class SerenityApp:
    def __init__(self, master):
        self.master = master
        self.master.title("NhyiraSys")
        self.master.geometry("1280x770+120+0")
        customtkinter.set_appearance_mode('light')
        customtkinter.set_default_color_theme("dark-blue")
        self.church_ID = customtkinter.StringVar()  

        self.backend = backend
        backend.connect()
 
        # Initialize authentication UI
        self.auth_ui = AuthUI(master, self)
        self.auth_ui.show_login()
        self.PRIMARY_BG = "#1A2233"

        self.church_ID = customtkinter.StringVar()

    # These methods are called by the dashboard navigation buttons
    def show_dashboard(self):
        self.dashboard_ui = DashboardUI(self.master, self) 

    def show_finance(self):
        """Show finance authentication dialog"""
        # Modal dialog for password
        self.finance_modal = customtkinter.CTkToplevel(self.master)
        self.finance_modal.title("Finance Authentication")
        self.finance_modal.geometry("350x180+500+250")
        self.finance_modal.grab_set()
        self.finance_modal.focus_force()
        self.finance_modal.resizable(False, False)
        
        # Add protocol handler for window close
        self.finance_modal.protocol("WM_DELETE_WINDOW", self.on_finance_modal_close)

        customtkinter.CTkLabel(
            self.finance_modal, text="Enter Admin Password", 
            font=("Montserrat", 16, "bold")
        ).pack(pady=(25, 10))

        self.confirmEntry = customtkinter.CTkEntry(
            self.finance_modal, placeholder_text="Password", 
            width=220, show="*"
        )
        self.confirmEntry.pack(pady=10)
        self.confirmEntry.focus_set()
        self.confirmEntry.bind('<Return>', lambda e: self.show_finance_auth())
    
        submit_btn = customtkinter.CTkButton(
            self.finance_modal, text="Login", 
            fg_color="#00BACE", 
            command=self.show_finance_auth
        )
        submit_btn.pack(pady=(5, 15))

    def on_finance_modal_close(self):
        """Handle modal window close"""
        self.finance_modal.destroy()
        self.finance_modal = None

    def show_finance_auth(self, event=None):
        """Authenticate user for finance access"""
        try:
            password = self.confirmEntry.get().strip()
            
            if not password:
                messagebox.showwarning("Input Error", "Please enter a password")
                return
            
            church_id = getattr(self, 'current_church_id', None) or self.church_ID.get()
            if not church_id:
                messagebox.showerror("Session Error", "No active church session found.\nPlease login again.")
                if hasattr(self, 'finance_modal') and self.finance_modal:
                    self.finance_modal.destroy()
                self.auth_ui.show_login()
                return
                
            if backend.verify_church(church_id, password):
                if hasattr(self, 'finance_modal') and self.finance_modal:
                    self.finance_modal.destroy()
                self.finance_ui = FinanceUI(self.master, self)
            else:
                messagebox.showerror("Login Error", "Incorrect Admin Password\nPlease try again")
                if hasattr(self, 'finance_modal') and self.finance_modal and self.confirmEntry.winfo_exists():
                    self.confirmEntry.delete(0, "end")
                    self.confirmEntry.focus_set()
        except Exception as e:
            messagebox.showerror("Login Error", f"Authentication failed: {str(e)}")
            if hasattr(self, 'finance_modal') and self.finance_modal and self.confirmEntry.winfo_exists():
                self.confirmEntry.delete(0, "end")
                self.confirmEntry.focus_set()


    def show_attendance(self):
       self.attendance_ui = AttendanceUI(self.master, self)

    def show_head_remittance(self):
        """Show head church remittance window"""
        if not hasattr(self, 'current_church_id'):
            messagebox.showerror("Session Error", "No active church session")
            return
        
        self.remittance_win = HeadChurchRemitWindow(self.master, self.current_church_id, self.backend)
        self.remittance_win.attributes('-topmost', True)
        self.remittance_win.focus_force()

    def show_messaging(self):
        self.message_ui = MessagingUI(self.master, self)

    def show_developers(self):
        import webbrowser
        from PIL import Image, ImageTk

        # Clear the main window
        for widget in self.master.winfo_children():
            widget.destroy()

        card = customtkinter.CTkFrame(self.master, fg_color="#F5F5F5", corner_radius=22)
        card.place(relx=0.5, rely=0.5, anchor="c", relwidth=0.52, relheight=0.62)
        try:
            logo_img = Image.open("img1/detailLogo.png").resize((90, 90))
            logo = customtkinter.CTkImage(light_image=logo_img, dark_image=logo_img, size=(90, 90))
            logo_label = customtkinter.CTkLabel(card, image=logo, text="")
            logo_label.pack(pady=(28, 8))
        except Exception:
            customtkinter.CTkLabel(
                card, text="NhyiraSys", font=("Montserrat Alternates", 28, "bold"), text_color="#00BACE"
            ).pack(pady=(28, 8))

        customtkinter.CTkLabel(
            card,
            text="About the Developer",
            font=("Montserrat", 22, "bold"),
            text_color="#26658C"
        ).pack(pady=(0, 8))

        customtkinter.CTkFrame(card, height=2, fg_color="#54ACBF").pack(fill="x", padx=30, pady=(0, 18))


        customtkinter.CTkLabel(
            card,
            text="NhyiraSys is a modern church management solution\ncrafted with passion by:",
            font=("Montserrat", 14),
            text_color="#333",
            justify="center"
        ).pack(pady=(0, 2))

        customtkinter.CTkLabel(
            card,
            text="VARTSY SYSTEMS",
            font=("Montserrat", 20, "bold"),
            text_color="#00BACE"
        ).pack(pady=(0, 10))
        def copy_email():
            self.master.clipboard_clear()
            self.master.clipboard_append("info@vartsysystems.com")
            messagebox.showinfo("Copied", "Email address copied to clipboard!")

        email_label = customtkinter.CTkLabel(
            card,
            text="info@vartsysystems.com",
            font=("Montserrat", 15, "underline"),
            text_color="#26658C",
            cursor="hand2"
        )
        email_label.pack()
        email_label.bind("<Button-1>", lambda e: copy_email())

        def open_website(event=None):
            webbrowser.open("https://www.vartsysystems.com")

        website_label = customtkinter.CTkLabel(
            card,
            text="www.vartsysystems.com",
            font=("Montserrat", 15, "underline"),
            text_color="#26658C",
            cursor="hand2"
        )
        website_label.pack(pady=(0, 10))
        website_label.bind("<Button-1>", open_website)

        # More info
        customtkinter.CTkLabel(
            card,
            text="We specialize in digital solutions for organizations, churches, and businesses.\n"
                 "Contact us for custom software, websites, and IT consulting.",
            font=("Montserrat", 14),
            text_color="#444",
            justify="center"
        ).pack(pady=(0, 16))
        def open_linkedin(event=None):
            webbrowser.open("https://www.linkedin.com/company/vartsy-systems")

        linkedin_label = customtkinter.CTkLabel(
            card,
            text="LinkedIn",
            font=("Montserrat", 14, "underline"),
            text_color="#0077B5",
            cursor="hand2"
        )
        linkedin_label.pack()
        linkedin_label.bind("<Button-1>", open_linkedin)
 
        close_btn = customtkinter.CTkButton( 
            card,
            text="X",
            font=("Montserrat", 18, "bold"),
            fg_color="transparent",
            hover_color="#54ACBF",
            text_color="red",
            width=10,
            corner_radius=8,
            command=self.show_dashboard
        )
        close_btn.place(relx=0.02, rely=0.02, anchor="nw")

        # Copyright
        customtkinter.CTkLabel(
            card,
            text="© 2025 NhyiraSys. All rights reserved.",
            font=("Montserrat", 11),
            text_color="#888"
        ).pack(side="bottom", pady=10)

    def switchMode(self):
     
        mode = customtkinter.get_appearance_mode()
        if mode == "Dark":
            customtkinter.set_appearance_mode("light")
        else:
            customtkinter.set_appearance_mode("dark")

  
    def count_all(self, church_id):
        return backend.count_all_members(church_id)

    def count_male(self, church_id):
        return backend.count_male_members(church_id)

    def count_female(self, church_id):
        return backend.count_female_members(church_id)

    def on_login_success(self, church_id):
        """Handle successful login"""
        self.church_ID.set(church_id)
        self.current_church_id = church_id 
        self.show_dashboard()
        self.dashboard_ui.church_name = self.dashboard_ui.get_church_name(church_id)
        self.dashboard_ui.usernameLabel.configure(text=self.dashboard_ui.church_name)

if __name__ == "__main__":
    window = customtkinter.CTk()
    start = time.time()
    app = SerenityApp(window)
    window.iconbitmap('img1/navIco.ico')
    window.mainloop()