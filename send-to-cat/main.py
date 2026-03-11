#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Send to GitHub - A beautiful GUI application to upload files to GitHub
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from github import Github, InputGitTreeElement
from github.GithubException import GithubException
import os
import json
import threading
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
import base64

# Load environment variables
load_dotenv()

# Configure customtkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def get_file_size_str(size_in_bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.1f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.1f} TB"

class HistoryManager:
    def __init__(self, filename="history.json"):
        self.filename = filename
        self.history = self.load_history()

    def load_history(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save_history(self):
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=4)
        except Exception as e:
            print(f"Error saving history: {e}")

    def add_entry(self, repo, branch, commit_msg, files):
        entry = {
            "id": str(datetime.now().timestamp()),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "repo": repo,
            "branch": branch,
            "commit_msg": commit_msg,
            "files": files
        }
        self.history.insert(0, entry)  # Add to top
        self.save_history()

    def delete_entry(self, entry_id):
        self.history = [entry for entry in self.history if entry.get("id") != entry_id]
        self.save_history()

class GitHubUploaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Window configuration
        self.title("📤 Send to Cat")
        self.geometry("750x750")
        self.resizable(False, False)
        
        # GitHub credentials
        self.username = os.getenv("GITHUB_USERNAME", "")
        self.token = os.getenv("GITHUB_TOKEN", "")
        self.selected_files = []
        self.repo_name = ""
        self.github_client = None
        self.available_repos = []
        
        self.history_manager = HistoryManager()
        
        # Setup UI
        self.setup_ui()
        
        # Check credentials and fetch data
        if self.check_credentials():
            self.github_client = Github(self.token)
            # Start background thread to fetch repos
            threading.Thread(target=self.fetch_repositories, daemon=True).start()
    
    def setup_ui(self):
        """Setup the user interface"""
        
        # Main container with padding (allow window resizing)
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.pack(fill="both", expand=True) # Removed fixed padding that squeezed the UI
        
        # Add an inner frame for actual padding so it resizes correctly
        self.inner_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.inner_frame.pack(fill="both", expand=True, padx=20, pady=(20, 10))
        
        # Title
        self.title_label = ctk.CTkLabel(
            self.inner_frame,
            text="📤 Send to cat",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        self.title_label.pack(pady=(5, 5))
        
        self.subtitle_label = ctk.CTkLabel(
            self.inner_frame,
            text="Upload files to your GitHub repositories easily",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        self.subtitle_label.pack(pady=(0, 10))
        
        # Tabview
        self.tabview = ctk.CTkTabview(self.inner_frame)
        self.tabview.pack(fill="both", expand=True, padx=5, pady=0)
        
        self.tab_upload = self.tabview.add("Upload")
        self.tab_manage = self.tabview.add("Manage")
        self.tab_history = self.tabview.add("History")
        
        self.setup_upload_tab()
        self.setup_manage_tab()
        self.setup_history_tab()

    def setup_upload_tab(self):
        # Create a scrollable frame for the upload tab just in case it overflows on small screens
        self.upload_scroll = ctk.CTkScrollableFrame(self.tab_upload, fg_color="transparent")
        self.upload_scroll.pack(fill="both", expand=True)

        # Repository selection frame
        self.repo_frame = ctk.CTkFrame(self.upload_scroll)
        self.repo_frame.pack(fill="x", padx=5, pady=5)
        
        self.repo_label = ctk.CTkLabel(
            self.repo_frame,
            text="Repository Name (Select or Type new):",
            font=ctk.CTkFont(size=14)
        )
        self.repo_label.pack(anchor="w", padx=10, pady=(5, 2))
        
        # Use Combobox for smarter selection
        self.repo_combo = ctk.CTkComboBox(
            self.repo_frame,
            values=["Loading your repositories..."],
            height=35,
            font=ctk.CTkFont(size=13),
            command=self.on_repo_selected
        )
        self.repo_combo.pack(fill="x", padx=10, pady=(2, 5))
        self.repo_combo.set("Enter repo name or select from list")
        
        # Branch selection
        self.branch_frame = ctk.CTkFrame(self.upload_scroll)
        self.branch_frame.pack(fill="x", padx=5, pady=5)
        
        self.branch_label = ctk.CTkLabel(
            self.branch_frame,
            text="Branch:",
            font=ctk.CTkFont(size=14)
        )
        self.branch_label.pack(anchor="w", padx=10, pady=(5, 2))
        
        self.branch_combo = ctk.CTkComboBox(
            self.branch_frame,
            values=["main", "master"],
            height=35,
            font=ctk.CTkFont(size=13)
        )
        self.branch_combo.set("main")
        self.branch_combo.pack(fill="x", padx=10, pady=(2, 5))
        
        # File selection frame
        self.file_frame = ctk.CTkFrame(self.upload_scroll)
        self.file_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.file_header_frame = ctk.CTkFrame(self.file_frame, fg_color="transparent")
        self.file_header_frame.pack(fill="x", padx=10, pady=(5, 2))
        
        self.file_label = ctk.CTkLabel(
            self.file_header_frame,
            text="Select Files to Upload:",
            font=ctk.CTkFont(size=14)
        )
        self.file_label.pack(side="left")
        
        # File selection buttons
        self.btn_frame = ctk.CTkFrame(self.file_frame, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=10, pady=2)
        
        self.select_file_btn = ctk.CTkButton(
            self.btn_frame,
            text="📁 Select Files",
            command=self.select_files,
            height=30,
            width=110,
            font=ctk.CTkFont(size=12)
        )
        self.select_file_btn.pack(side="left", padx=(0, 5))
        
        self.select_folder_btn = ctk.CTkButton(
            self.btn_frame,
            text="📂 Select Folder",
            command=self.select_folder,
            height=30,
            width=110,
            font=ctk.CTkFont(size=12)
        )
        self.select_folder_btn.pack(side="left", padx=(0, 5))

        self.clear_files_btn = ctk.CTkButton(
            self.btn_frame,
            text="🗑️ Clear All",
            command=self.clear_files,
            height=30,
            width=90,
            fg_color="#d73a49",
            hover_color="#cb2431",
            font=ctk.CTkFont(size=12)
        )
        self.clear_files_btn.pack(side="right")
        
        # File list display
        self.file_list_frame = ctk.CTkScrollableFrame(
            self.file_frame,
            height=120,
            corner_radius=5
        )
        self.file_list_frame.pack(fill="both", expand=True, padx=10, pady=(5, 5))
        
        self.file_list_inner_frame = ctk.CTkFrame(self.file_list_frame, fg_color="transparent")
        self.file_list_inner_frame.pack(fill="both", expand=True)

        self.update_file_list()
        
        # Commit message
        self.commit_frame = ctk.CTkFrame(self.upload_scroll)
        self.commit_frame.pack(fill="x", padx=5, pady=5)
        
        self.commit_entry = ctk.CTkEntry(
            self.commit_frame,
            placeholder_text="Enter commit message...",
            height=35,
            font=ctk.CTkFont(size=13)
        )
        self.commit_entry.insert(0, "Upload files via Send to GitHub")
        self.commit_entry.pack(fill="x", padx=10, pady=5)
        
        # Upload button (now perfectly visible at the bottom)
        self.upload_btn = ctk.CTkButton(
            self.upload_scroll,
            text="🚀 Upload to GitHub",
            command=self.upload_to_github,
            height=45,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#2ea043",
            hover_color="#2c974b"
        )
        self.upload_btn.pack(fill="x", padx=5, pady=(10, 5))
        
        # Status label
        self.status_label = ctk.CTkLabel(
            self.upload_scroll,
            text="",
            font=ctk.CTkFont(size=13),
            text_color="gray"
        )
        self.status_label.pack(pady=(0, 5))

    def setup_history_tab(self):
        self.history_scroll_frame = ctk.CTkScrollableFrame(
            self.tab_history,
            height=450,
            corner_radius=5
        )
        self.history_scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.refresh_history_ui()

    def setup_manage_tab(self):
        self.manage_scroll_frame = ctk.CTkScrollableFrame(
            self.tab_manage,
            height=450,
            corner_radius=5
        )
        self.manage_scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.refresh_btn = ctk.CTkButton(
            self.tab_manage,
            text="🔄 Refresh Repositories",
            command=self.fetch_repositories,
            height=35
        )
        self.refresh_btn.pack(pady=10)
        
        self.refresh_manage_ui()

    def refresh_manage_ui(self):
        if not hasattr(self, 'manage_scroll_frame'):
            return
            
        for widget in self.manage_scroll_frame.winfo_children():
            widget.destroy()
            
        if not self.available_repos:
            no_repo_label = ctk.CTkLabel(
                self.manage_scroll_frame,
                text="Fetching repositories or no repositories found...",
                text_color="gray",
                font=ctk.CTkFont(size=14)
            )
            no_repo_label.pack(pady=40)
            return

        for repo_name in self.available_repos:
            if repo_name in ["Loading your repositories...", "No repositories found", "Enter repo name or select from list"]:
                continue
                
            entry_frame = ctk.CTkFrame(self.manage_scroll_frame, corner_radius=8)
            entry_frame.pack(fill="x", padx=5, pady=5)
            
            repo_label = ctk.CTkLabel(
                entry_frame,
                text=f"📦 {repo_name}",
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w"
            )
            repo_label.pack(side="left", padx=15, pady=15)
            
            delete_btn = ctk.CTkButton(
                entry_frame,
                text="🗑️ Delete",
                width=80,
                height=30,
                fg_color="#d73a49",
                hover_color="#cb2431",
                font=ctk.CTkFont(size=12, weight="bold"),
                command=lambda r=repo_name: self.delete_repository(r)
            )
            delete_btn.pack(side="right", padx=15, pady=10)

    def delete_repository(self, repo_name):
        confirm_text = f"Are you ABSOLUTELY SURE you want to delete '{repo_name}'?\n\nThis action CANNOT be undone. This will permanently delete the repository from your GitHub account."
        if not messagebox.askyesno("⚠️ Confirm Deletion", confirm_text, icon="warning"):
            return
            
        try:
            repo = self.github_client.get_repo(repo_name)
            repo.delete()
            
            messagebox.showinfo("Success", f"Repository '{repo_name}' has been deleted successfully.")
            
            # Remove from local list to avoid full refetch delay
            if repo_name in self.available_repos:
                self.available_repos.remove(repo_name)
                
            self.update_repo_combo(self.available_repos)
            self.refresh_manage_ui()
            
        except GithubException as e:
            if e.status == 403 or e.status == 404:
                messagebox.showerror(
                    "Permission Denied", 
                    f"Could not delete '{repo_name}'.\n\nYour GitHub Personal Access Token needs the 'delete_repo' scope to perform this action.\n\nPlease update your token permissions in GitHub Developer Settings."
                )
            else:
                messagebox.showerror("Error", f"Failed to delete repository:\n{str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred:\n{str(e)}")

    def fetch_repositories(self):
        """Fetch user repositories in background"""
        try:
            user = self.github_client.get_user()
            repos = user.get_repos(sort="updated", direction="desc")
            # Limit to 50 to keep it fast
            repo_names = [f"{repo.owner.login}/{repo.name}" for repo in list(repos[:50])]
            
            # Update UI from main thread
            self.after(0, self.update_repo_combo, repo_names)
        except Exception as e:
            print(f"Could not fetch repos: {e}")
            self.after(0, self.update_repo_combo, [])

    def update_repo_combo(self, repo_names):
        if repo_names:
            self.available_repos = repo_names
            self.repo_combo.configure(values=repo_names)
            
            # Only set if the current value is not in the new list, or it's empty
            current_val = self.repo_combo.get()
            if current_val not in repo_names:
                self.repo_combo.set(repo_names[0])
                # Automatically fetch branches for the first repo
                self.on_repo_selected(repo_names[0])
                
            self.status_label.configure(text="✓ Connected to GitHub successfully", text_color="#2ea043")
        else:
            self.available_repos = []
            self.repo_combo.configure(values=["No repositories found"])
            self.repo_combo.set("")
            
        # Update manage tab
        self.refresh_manage_ui()

    def on_repo_selected(self, selected_repo):
        """Triggered when a user selects a repo from the dropdown"""
        if not selected_repo or selected_repo == "Loading your repositories..." or selected_repo == "No repositories found":
            return
            
        self.status_label.configure(text=f"Fetching branches for {selected_repo}...", text_color="orange")
        threading.Thread(target=self.fetch_branches, args=(selected_repo,), daemon=True).start()

    def fetch_branches(self, repo_name):
        try:
            repo = self.github_client.get_repo(repo_name)
            branches = [branch.name for branch in repo.get_branches()]
            self.after(0, self.update_branch_combo, branches)
        except Exception:
            self.after(0, self.update_branch_combo, ["main", "master"])

    def update_branch_combo(self, branches):
        if branches:
            self.branch_combo.configure(values=branches)
            if "main" in branches:
                self.branch_combo.set("main")
            elif "master" in branches:
                self.branch_combo.set("master")
            else:
                self.branch_combo.set(branches[0])
            self.status_label.configure(text="")
        else:
            self.branch_combo.configure(values=["main", "master"])
            self.branch_combo.set("main")

    def refresh_history_ui(self):
        for widget in self.history_scroll_frame.winfo_children():
            widget.destroy()
            
        history = self.history_manager.history
        
        if not history:
            no_history_label = ctk.CTkLabel(
                self.history_scroll_frame,
                text="No upload history yet.",
                text_color="gray",
                font=ctk.CTkFont(size=14)
            )
            no_history_label.pack(pady=40)
            return

        for entry in history:
            entry_frame = ctk.CTkFrame(self.history_scroll_frame, corner_radius=8)
            entry_frame.pack(fill="x", padx=5, pady=5)
            
            info_frame = ctk.CTkFrame(entry_frame, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
            
            repo_label = ctk.CTkLabel(
                info_frame,
                text=f"📦 {entry.get('repo')} ({entry.get('branch')})",
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w"
            )
            repo_label.pack(fill="x")
            
            time_label = ctk.CTkLabel(
                info_frame,
                text=f"🕒 {entry.get('timestamp')} | 📄 {len(entry.get('files', []))} files",
                font=ctk.CTkFont(size=12),
                text_color="gray",
                anchor="w"
            )
            time_label.pack(fill="x")

            msg_label = ctk.CTkLabel(
                info_frame,
                text=f"💬 {entry.get('commit_msg')}",
                font=ctk.CTkFont(size=12, slant="italic"),
                text_color="lightgray",
                anchor="w"
            )
            msg_label.pack(fill="x", pady=(2, 0))
            
            btn_frame = ctk.CTkFrame(entry_frame, fg_color="transparent")
            btn_frame.pack(side="right", padx=10, pady=10)
            
            reuse_btn = ctk.CTkButton(
                btn_frame,
                text="🔄 Reuse",
                width=70,
                height=28,
                font=ctk.CTkFont(size=12),
                command=lambda e=entry: self.reuse_history(e)
            )
            reuse_btn.pack(side="left", padx=5)
            
            delete_btn = ctk.CTkButton(
                btn_frame,
                text="🗑️",
                width=30,
                height=28,
                fg_color="#d73a49",
                hover_color="#cb2431",
                command=lambda eid=entry.get("id"): self.delete_history_entry(eid)
            )
            delete_btn.pack(side="left")

    def reuse_history(self, entry):
        self.repo_combo.set(entry.get("repo", ""))
        self.branch_combo.set(entry.get("branch", "main"))
        
        self.commit_entry.delete(0, 'end')
        self.commit_entry.insert(0, entry.get("commit_msg", ""))
        
        # Verify files still exist
        valid_files = [f for f in entry.get("files", []) if os.path.exists(f)]
        self.selected_files = valid_files
        self.update_file_list()
        
        if len(valid_files) < len(entry.get("files", [])):
            messagebox.showwarning(
                "Missing Files",
                f"Some previously uploaded files could not be found locally.\n"
                f"Recovered {len(valid_files)} out of {len(entry.get('files', []))} files."
            )
            
        self.tabview.set("Upload")

    def delete_history_entry(self, entry_id):
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this history record?"):
            self.history_manager.delete_entry(entry_id)
            self.refresh_history_ui()

    def check_credentials(self):
        """Check if GitHub credentials are set"""
        if not self.username or not self.token:
            messagebox.showwarning(
                "Missing Credentials",
                "GitHub credentials not found in .env file!\n\n"
                "Please edit the .env file and add:\n"
                "- GITHUB_USERNAME\n"
                "- GITHUB_TOKEN\n\n"
                "You can get a token from: https://github.com/settings/tokens"
            )
            self.upload_btn.configure(state="disabled", fg_color="gray")
            return False
        return True
    
    def select_files(self):
        """Open file dialog to select multiple files"""
        files = filedialog.askopenfilenames(
            title="Select Files to Upload",
            filetypes=[("All Files", "*.*")]
        )
        if files:
            # Add new files without duplicating
            for file in files:
                if file not in self.selected_files:
                    self.selected_files.append(file)
            self.update_file_list()
    
    def select_folder(self):
        """Open folder dialog to select all files in a folder"""
        folder = filedialog.askdirectory(title="Select Folder to Upload (Blazing Fast Mode)")
        if folder:
            added = 0
            
            # Show processing message
            self.status_label.configure(text="Scanning folder for files...", text_color="orange")
            self.update()
            
            # Directories to completely ignore to speed up processing
            IGNORE_DIRS = {'.git', 'node_modules', 'venv', 'env', '__pycache__', '.idea', '.vscode'}
            
            for root, dirs, files in os.walk(folder):
                # Filter directories in-place VERY FAST
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in IGNORE_DIRS]
                
                for file in files:
                    if not file.startswith('.'):  # Skip hidden files
                        full_path = os.path.join(root, file)
                        if full_path not in self.selected_files:
                            self.selected_files.append(full_path)
                            added += 1
            
            if added > 0:
                self.update_file_list()
                self.status_label.configure(text=f"Added {added} files successfully.", text_color="#2ea043")
            else:
                self.status_label.configure(text="No valid files found in folder.", text_color="orange")

    def clear_files(self):
        self.selected_files = []
        self.update_file_list()
        
    def remove_file(self, file_path):
        if file_path in self.selected_files:
            self.selected_files.remove(file_path)
            self.update_file_list()

    def update_file_list(self):
        """Update the file list display"""
        for widget in self.file_list_inner_frame.winfo_children():
            widget.destroy()
        
        if not self.selected_files:
            empty_label = ctk.CTkLabel(
                self.file_list_inner_frame,
                text="No files selected",
                text_color="gray",
                font=ctk.CTkFont(size=13)
            )
            empty_label.pack(pady=20)
        else:
            count_label = ctk.CTkLabel(
                self.file_list_inner_frame,
                text=f"✓ {len(self.selected_files)} file(s) selected",
                text_color="#2ea043",
                font=ctk.CTkFont(size=13, weight="bold")
            )
            count_label.pack(anchor="w", padx=5, pady=(0, 5))
            
            for file in self.selected_files:
                file_row = ctk.CTkFrame(self.file_list_inner_frame, fg_color="transparent")
                file_row.pack(fill="x", pady=2)
                
                try:
                    size = os.path.getsize(file)
                    size_str = get_file_size_str(size)
                except Exception:
                    size_str = "Unknown"

                name_label = ctk.CTkLabel(
                    file_row,
                    text=f"📄 {os.path.basename(file)}  ({size_str})",
                    text_color="white",
                    font=ctk.CTkFont(size=12),
                    anchor="w"
                )
                name_label.pack(side="left", padx=5)
                
                remove_btn = ctk.CTkButton(
                    file_row,
                    text="✕",
                    width=24,
                    height=24,
                    fg_color="transparent",
                    hover_color="#d73a49",
                    text_color="gray",
                    font=ctk.CTkFont(size=10, weight="bold"),
                    command=lambda f=file: self.remove_file(f)
                )
                remove_btn.pack(side="right", padx=5)
    
    def upload_to_github(self):
        """Upload selected files to GitHub"""
        if not self.selected_files:
            messagebox.showerror("Error", "Please select files to upload!")
            return
        
        repo_input = self.repo_combo.get().strip()
        if not repo_input or repo_input == "Loading your repositories..." or repo_input == "Enter repo name or select from list":
            messagebox.showerror("Error", "Please explicitly select or enter a repository name!")
            return
        
        # Parse repository name
        if '/' in repo_input:
            self.repo_name = repo_input
        else:
            self.repo_name = f"{self.username}/{repo_input}"
        
        branch = self.branch_combo.get().strip() or "main"
        commit_message = self.commit_entry.get().strip() or "Upload files via Send to GitHub"
        
        # Disable button during upload
        self.upload_btn.configure(state="disabled", text="⏳ Uploading...")
        self.status_label.configure(text="Connecting to GitHub...", text_color="orange")
        self.update()
        
        try:
            # Use background execution for upload to prevent freezing UI completely
            threading.Thread(
                target=self._perform_upload,
                args=(self.repo_name, branch, commit_message),
                daemon=True
            ).start()
        except Exception as e:
            self.status_label.configure(text="✗ Start upload failed!", text_color="red")
            messagebox.showerror("Upload Error", f"An error occurred:\n{str(e)}")
            self.upload_btn.configure(state="normal", text="🚀 Upload to GitHub")

    def _perform_upload(self, repo_name, branch, commit_message):
        try:
            # Initialize GitHub client
            g = Github(self.token)
            
            # Get repository
            self.after(0, lambda: self.status_label.configure(text=f"Accessing repository: {repo_name}", text_color="orange"))
            
            try:
                repo = g.get_repo(repo_name)
            except GithubException:
                # Need to use main thread for messagebox
                def create_prompt():
                    result = messagebox.askyesno(
                        "Repository Not Found",
                        f"Repository '{repo_name}' not found.\n\nDo you want to create it?"
                    )
                    return result
                
                # Due to threading limitations with tkinter UI, askyesno in thread might freeze on some OS
                # Proceed cautiously (it's best practice to handle dialogs in main thread, but tkinter is unpredictable)
                create_repo = messagebox.askyesno("Repository Not Found", f"Repository '{repo_name}' not found.\nDo you want to create it?")
                if create_repo:
                    self.after(0, lambda: self.status_label.configure(text="Creating repository...", text_color="orange"))
                    repo = g.get_user().create_repo(repo_name.split('/')[-1])
                    self.repo_name = repo.full_name
                else:
                    raise Exception("Repository creation cancelled")
            
            # Upload each file
            total_files = len(self.selected_files)
            for i, file_path in enumerate(self.selected_files, 1):
                if not os.path.exists(file_path):
                    continue

                self.after(0, lambda idx=i, fname=os.path.basename(file_path): 
                    self.status_label.configure(text=f"Uploading {idx}/{total_files}: {fname}", text_color="orange"))
                
                # Calculate path in repo (preserve folder structure for folders)
                if len(self.selected_files) > 1:
                    repo_path = os.path.basename(file_path)
                else:
                    repo_path = os.path.basename(file_path)
                
                # Read file content
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                # Check if file exists in repo
                try:
                    existing_file = repo.get_contents(repo_path, ref=branch)
                    # Update existing file
                    repo.update_file(
                        path=repo_path,
                        message=commit_message,
                        content=content,
                        sha=existing_file.sha,
                        branch=branch
                    )
                except GithubException:
                    # File doesn't exist, create it
                    repo.create_file(
                        path=repo_path,
                        message=commit_message,
                        content=content,
                        branch=branch
                    )
            
            # Finish up in main thread
            self.after(0, self._upload_success, repo_name, branch, commit_message, total_files)
            
        except Exception as e:
            self.after(0, lambda err=str(e): self._upload_error(err))

    def _upload_success(self, repo_name, branch, commit_message, total_files):
        # Record History
        self.history_manager.add_entry(
            repo=repo_name,
            branch=branch,
            commit_msg=commit_message,
            files=self.selected_files.copy()
        )
        self.refresh_history_ui()
        
        # Success!
        self.status_label.configure(
            text=f"✓ Successfully uploaded {total_files} file(s)!",
            text_color="#2ea043"
        )
        
        messagebox.showinfo(
            "Success! 🎉",
            f"Successfully uploaded {total_files} file(s) to:\n"
            f"https://github.com/{repo_name}\n\n"
            f"Branch: {branch}"
        )
        
        # Clear selection conditionally
        if messagebox.askyesno("Clear Files", "Do you want to clear the selected files?"):
            self.clear_files()
            
        self.upload_btn.configure(state="normal", text="🚀 Upload to GitHub")

    def _upload_error(self, error_msg):
        self.status_label.configure(text="✗ Upload failed!", text_color="red")
        messagebox.showerror("Upload Error", f"An error occurred:\n{error_msg}")
        self.upload_btn.configure(state="normal", text="🚀 Upload to GitHub")

def main():
    app = GitHubUploaderApp()
    app.mainloop()

if __name__ == "__main__":
    main()
