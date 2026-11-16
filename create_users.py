from django.contrib.auth import get_user_model
import secrets, string

User = get_user_model()

def gen_password(length=12):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

accounts = [
    {'username': 'frank',      'role': 'owner',     'full_name': 'Frank'},
    {'username': 'attendant1', 'role': 'attendant',  'full_name': 'Attendant 1'},
    {'username': 'attendant2', 'role': 'attendant',  'full_name': 'Attendant 2'},
]

print('=' * 50)
for acc in accounts:
    password = gen_password()
    user, created = User.objects.get_or_create(username=acc['username'])
    user.role = acc['role']
    user.full_name = acc['full_name']
    user.set_password(password)
    user.save()
    status = 'CREATED' if created else 'UPDATED'
    print(status + ': username=' + acc['username'] + '  password=' + password + '  role=' + acc['role'])
print('=' * 50)
print('SAVE THESE PASSWORDS NOW - they cannot be retrieved again.')
