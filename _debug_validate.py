import io
import traceback
from werkzeug.security import generate_password_hash
import app as m

app = m.app
db = m.db
User = m.User

app.config['TESTING'] = True

with app.app_context():
    db.create_all()
    u = User.query.filter_by(username='tmp_user_500').first()
    if not u:
        u = User(
            username='tmp_user_500',
            email='tmp_user_500@example.com',
            password_hash=generate_password_hash('pass1234')
        )
        db.session.add(u)
        db.session.commit()

client = app.test_client()
resp = client.post('/login', data={'username': 'tmp_user_500', 'password': 'pass1234'}, follow_redirects=True)
print('login', resp.status_code)

try:
    data = {'simulation_mode': '1', 'video_file': (io.BytesIO(b'fakevid'), 'sample_rc.mp4')}
    r = client.post('/validate', data=data, content_type='multipart/form-data', follow_redirects=False)
    print('validate status', r.status_code)
    print('location', r.headers.get('Location'))
    print(r.data[:300])
except Exception:
    traceback.print_exc()
