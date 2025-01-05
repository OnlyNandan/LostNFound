# **Lost and Found Website** 🌐

Welcome to the **Lost and Found Website**, a **Python Flask** web application designed to help people **find lost items** in a community or college environment. This project utilizes **Flask**, **MySQL**, and is hosted on **PythonAnywhere** to provide an easy and efficient platform for reporting and searching lost items.

---

## 🚀 **Features**
- **Add Lost Items**: Users can **report lost items** with detailed descriptions and images.
- **Search for Lost Items**: Easily **search** for lost items by description, category, or status.
- **Admin Control**: Admins have the ability to **approve** or **reject** lost item reports.
- **Database Integration**: The app is powered by **MySQL** for smooth storage and management of lost and found items.

---

## 🛠️ **Technologies Used**

- **Backend**: [Flask](https://flask.palletsprojects.com/) (Python web framework)
- **Database**: [MySQL](https://www.mysql.com/)
- **Hosting**: [PythonAnywhere](https://www.pythonanywhere.com/)
- **Frontend**: HTML, CSS, JavaScript (for building the user interface)

---

## ⚡ **Setup Instructions**

To run the app locally, follow these simple steps:

### 1. Clone the repository:
```bash
git clone https://github.com/yourusername/lost-and-found-website.git
```
### 2. Install the required dependencies:
```bash
pip install -r requirements.txt
```
### 3. Set up the MySQL Database:
- Create a new MySQL database and configure your database credentials in `config.py`.
- Initialize the database tables by running the appropriate SQL queries. The structure for the database is defined in the `models.py` file, which includes tables for lost items, users, and admins.

### 4. Configure the Flask App:
- Ensure the app is set up to connect to your MySQL database by updating the database connection details in `config.py`.

### 5. Run the app:
```bash
python3 app.py
```
- Open your browser and visit http://127.0.0.1:5000/ to access the Lost and Found website.
## 📝 Contributing

We welcome contributions to improve the project! If you want to add new features or fix bugs, feel free to open a pull request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## Star History

<a href="https://star-history.com/#OnlyNandan/LostNFound&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=OnlyNandan/LostNFound&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=OnlyNandan/LostNFound&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=OnlyNandan/LostNFound&type=Date" />
 </picture>
</a>
