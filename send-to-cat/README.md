# 📤 Send to GitHub

A beautiful and simple GUI application to upload files to GitHub repositories with ease.

## ✨ Features

- 🎨 Modern and beautiful dark theme interface
- 📁 Select individual files or entire folders
- 🔄 Automatically creates repositories if they don't exist
- 🌿 Support for custom branches
- 📝 Custom commit messages
- ⚡ Real-time upload status updates

## 🚀 Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure GitHub Credentials

Edit the `.env` file and add your GitHub credentials:

```env
GITHUB_USERNAME=your_username
GITHUB_TOKEN=your_personal_access_token
```

### Getting GitHub Token

1. Go to [GitHub Settings > Developer Settings > Personal Access Tokens](https://github.com/settings/tokens)
2. Click "Generate new token (classic)"
3. Give it a descriptive name
4. Select the **`repo`** scope (full control of private repositories)
5. Click "Generate token"
6. Copy the token and paste it in the `.env` file

## 📖 Usage

### Run the Application

```bash
python main.py
```

### How to Upload Files

1. **Enter Repository Name**: Type your repository name (e.g., `my-project` or `username/my-project`)
2. **Select Branch**: Choose the branch to upload to (default: `main`)
3. **Select Files**: Click "Select Files" or "Select Folder" to choose what to upload
4. **Commit Message**: Enter a custom commit message (optional)
5. **Upload**: Click "Upload to GitHub" button

## 📸 Screenshots

The application features:
- Clean dark theme interface
- File selection with preview
- Real-time upload progress
- Success/error notifications

## 🛠 Requirements

- Python 3.7+
- customtkinter
- PyGithub
- python-dotenv
- Pillow

## 📄 License

MIT License

## 🤝 Support

If you encounter any issues:
1. Make sure your GitHub token has the correct permissions
2. Check your internet connection
3. Verify the repository name is correct

---

Made with ❤️ using CustomTkinter
