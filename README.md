# Vehicle Company ERP Management System

A custom **Django ERP (Enterprise Resource Planning) system** designed to help businesses manage daily operations including sales, inventory, customers, employees, financial records, and business reporting.

The system was developed for a vehicle-related business workflow, replacing manual processes with a centralized digital management platform.

---

# Overview

This ERP platform provides a structured solution for managing business operations through multiple integrated modules.

The main goals of the system are:

- Centralized business data management
- Automated transaction tracking
- Inventory monitoring
- Customer and employee management
- Financial status tracking
- Professional reporting

The application is built with **Python, Django, and PostgreSQL** using a modular architecture for scalability and maintainability.

---

# Core Features

## Sales Management

- Daily sales transaction management
- Invoice generation
- Payment status tracking
- Customer transaction history
- Automated calculations
- Business transaction records

---

## Inventory Management

- Container and shipment inventory tracking
- Stock monitoring
- Inventory updates based on transactions
- Product/container records
- Inventory overview dashboard

---

## Customer Management

- Customer profiles
- Company records
- Transaction history
- Account management
- Customer-related reports

---

## Employee Management

- Employee records
- Role management
- Payroll-related information
- Employee reporting

---

## Financial Management & Reports

- Business financial tracking
- Transaction summaries
- Outstanding balance reports
- PDF report generation
- Exportable business documents

---

# Dashboard & Administration

The project includes a customized administration system using Django Jazzmin.

Administrators can manage:

- Users and permissions
- Customers
- Employees
- Sales records
- Inventory data
- Reports
- System content

The admin interface is optimized for easier management of daily business operations.

---

# Technology Stack

## Backend

- Python
- Django 5.1
- PostgreSQL
- Django ORM

## Frontend

- HTML5
- CSS3
- JavaScript
- Responsive UI

## Libraries & Tools

- django-jazzmin
- ReportLab
- WeasyPrint
- Pillow
- django-jalali

---

# Project Structure



vehicle-erp/
│
├── accounts/
│ └── Authentication, users, roles and profiles
│
├── daily_sale/
│ └── Sales transactions, invoices and payments
│
├── containers/
│ └── Inventory and shipment management
│
├── employee/
│ └── Employee records and management
│
├── reports/
│ └── Business reports and analytics
│
├── inventory_dashboard/
│ └── Django project configuration
│
├── static/
├── media/
├── manage.py
└── requirements.txt


---

# Application Architecture

The system follows Django's modular architecture.

User requests are handled through:



URLs
↓
Views
↓
Business Logic
↓
Models
↓
PostgreSQL Database


Each application module is responsible for a specific business domain.

The `daily_sale` module acts as the core operational module by managing transactions, invoices, payment tracking, and inventory-related updates.

---

# Automation Features

The system includes automated workflows such as:

- Automatic invoice numbering
- Transaction calculations
- Inventory updates
- Business summaries
- Report generation

These features reduce manual work and improve operational accuracy.

---

# Installation

## Clone Repository
git clone https://github.com/yourusername/vehicle-erp.git

cd vehicle-erp

# Create Virtual Environment
python -m venv .venv

# Activate environment:
Windows:
.venv\Scripts\activate

# Linux/Mac:
source .venv/bin/activate

# Install Dependencies:
pip install -r requirements.txt

# Configure Database
Create a PostgreSQL database and update your environment variables according to Django settings.

Example:
DATABASE_NAME=
DATABASE_USER=
DATABASE_PASSWORD=
DATABASE_HOST=
DATABASE_PORT=

# Run Migrations
python manage.py migrate

# Create Admin User
python manage.py createsuperuser

# Start Development Server
python manage.py runserver

# Application:
http://127.0.0.1:8000/

# Admin panel:
http://127.0.0.1:8000/admin/

# Production Considerations:

For production deployment:

Use environment variables for secrets
Disable DEBUG mode
Configure secure database credentials
Use Gunicorn/Nginx deployment
Configure static and media storage

# Project Highlights:
This project demonstrates practical experience in building business management software with:

ERP architecture
Django backend development
PostgreSQL database design
Role-based access control
Automated reporting
Business workflow automation

# Developer:
Shamsia Mohammadi

Python Django Backend Developer

Specialized in:

Django Web Applications
ERP Systems
Business Automation
Database-driven Platforms
E-commerce Solutions

# License:
This project is a demonstration of custom ERP development using Django.
