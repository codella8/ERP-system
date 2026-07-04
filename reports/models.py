from django.db import models

# The In-Out dashboard is a pure reporting layer: every number on the page is
# computed live (real-time) from data that already exists in the other apps:
#
#   - daily_sale.DailySaleTransaction / daily_sale.Payment  -> Sales & Cash-In
#   - expenses.Expense                                      -> Expenses & Cash-Out
#   - employee.SalaryPayment                                -> Cash-Out (salaries)
#   - containers.Inventory_List / containers.Container       -> Inventory & Container reports
#
# No new database tables are required, so this app intentionally has no
# models. The file is kept (as requested) so `inout` behaves like a normal
# Django app and so future report-specific models (e.g. saved filter
# presets) have an obvious place to live.
