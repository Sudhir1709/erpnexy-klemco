app_name = 'klemco_cs'
app_title = 'Klemco CS'
app_publisher = 'Klemco India'
app_description = 'Customer Service Module — Complaints, Order Execution, Dispatch'
app_version = '1.0.0'
app_icon = 'headset'
app_color = '#1A5276'
app_email = 'admin@klemcoindia.com'
app_license = 'MIT'

fixtures = [
    {'dt': 'Workspace', 'filters': [['app', '=', 'klemco_cs']]},
    {'dt': 'Role', 'filters': [['name', 'in', ['CS Executive', 'CS Manager', 'CS Supervisor']]]},
]

after_install = 'klemco_cs.setup.after_install'
