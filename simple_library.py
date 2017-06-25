import os, string
from datetime import datetime, timedelta

import logging
from logging.handlers import RotatingFileHandler

from flask import (
    Flask, request, render_template, jsonify, abort,
    url_for, redirect, flash, session, g)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import exc
from flask_login import (LoginManager, UserMixin, login_required,
                         login_user, logout_user, current_user)
from passlib.apps import custom_app_context as pwd_context
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import InputRequired, Email, Length, EqualTo
from flask_principal import (Principal, Permission, RoleNeed, AnonymousIdentity,
                             Identity, identity_changed, identity_loaded)

BORROW_PERIOD = 30  # days
DATE_FORMAT = "%Y-%m-%d"
# Stored procedures
GET_ROLES = """
            SELECT roles.name
            FROM users_roles
            JOIN roles ON users_roles.role_id = roles.id
            WHERE users_roles.user_id = '{0}'
            """

SET_ROLE = """
           INSERT INTO users_roles (user_id, role_id)
           SELECT users.id, roles.id FROM users CROSS JOIN roles
           WHERE users.username = '{0}' AND roles.name = '{1}'
           """

GET_BOOKS = """
            SELECT books.id, books.title, books.genre, books.isbn, books.year, books.author, count(copies.number) FROM
            books LEFT JOIN copies ON books.id = copies.book_id
            WHERE LOWER(books.title) LIKE LOWER('%%{0}%%')
            GROUP BY books.id ORDER BY books.id LIMIT {1} OFFSET {2}
            """

GET_BOOKS_BY_READER = """
            SELECT b1.id, b1.title, b1.genre,  b1.isbn, b1.year,  b1.author, c1.borrow_date, c1.return_date, c1.number
            FROM copies c1 INNER JOIN users u1 ON c1.reader_id = u1.id
            INNER JOIN books b1 ON c1.book_id=b1.id 
            WHERE NOT c1.is_presented AND u1.username='{0}'
            LIMIT {1} OFFSET {2}
            """

app = Flask(__name__)
app.config.update(
    DEBUG=True,
    SECRET_KEY=os.urandom(16).encode('base-64'),
    SQLALCHEMY_DATABASE_URI='postgresql://admin:admin@localhost/mytest',
    SQLALCHEMY_COMMIT_ON_TEARDOWN=True
)
app.debug = True

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

principals = Principal(app)

# Needs
be_admin = RoleNeed('admin')
be_user = RoleNeed('user')
app_needs = {
    'admin': be_admin,
    'user': be_user
}
admin_perm = Permission(be_admin)
admin_perm.description = "Admin's permissions"
user_perm = Permission(be_user)
user_perm.description = "User's permissions"
app_perms = [admin_perm, user_perm]
DEFAULT_ROLE = be_user


@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    identity.user = current_user
    roles = get_roles(current_user.id)

    for role in roles:
        identity.provides.add(app_needs[role])


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def get_roles(user_id):
    """
    Get list of roles for particular user
    :param user_id: User ID
    :return: List of Roles
    """
    return map(lambda x: str(dict(x)[u'name']), db.engine.execute(GET_ROLES.format(int(user_id))))


# Forms
class LoginForm(FlaskForm):
    username = StringField('username', validators=[InputRequired(), Length(min=3, max=20)])
    password = PasswordField('password', validators=[InputRequired(), Length(min=8, max=20)])
    remember = BooleanField('remember')


class RegisterForm(FlaskForm):
    email = StringField('email', validators=[InputRequired(), Email(message='Invalid e-mail'), Length(min=3, max=20)])
    username = StringField('username', validators=[InputRequired(), Length(min=3, max=20)])
    password = PasswordField('password', validators=[InputRequired(), Length(min=6, max=20),
                                                     EqualTo('confirm', message='Passwords must match')])
    # password = PasswordField('password', validators=[DataRequired()])
    confirm = PasswordField('confirm', validators=[InputRequired(), Length(min=6, max=20)])


# Models
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True)
    email = db.Column(db.String(20), unique=True)
    pass_hash = db.Column(db.String(128))
    phone = db.Column(db.String(20))
    active = db.Column(db.Boolean())

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.pass_hash = self.encrypt_pass(password)

    def encrypt_pass(self, password):
        enc_res = pwd_context.encrypt(password)
        self.pass_hash = enc_res
        return enc_res

    def verify_pass(self, password):
        return pwd_context.verify(password, self.pass_hash)


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True)
    desc = db.Column(db.String(255))

    def __init__(self, name):
        self.name = name


class Book(db.Model):
    __tablename__ = 'books'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    genre = db.Column(db.String(50))
    isbn = db.Column(db.String(13), unique=True)
    year = db.Column(db.Integer)
    author = db.Column(db.String(20))

    def __init__(self, title, genre, isbn, year, author):
        self.title = title
        self.genre = genre
        self.isbn = isbn
        self.year = year
        self.author = author

    def __repr__(self):
        return '<Book %r' % self.isbn

    def as_dict(self):
        return {c.title: getattr(self, c.title) for c in self.__table__.columns}

    @property
    def serialize(self):
        """Return object data in easily serializable format"""
        return {
            'id': self.id,
            'title': self.title,
            'genre': self.genre,
            'isbn': self.isbn,
            'year': self.year,
            'author': self.author
        }


class Copy(db.Model):
    __tablename__ = 'copies'
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'))
    reader_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_presented = db.Column(db.Boolean)
    borrow_date = db.Column(db.Date)
    return_date = db.Column(db.Date)

    def __init__(self, book_id, number):
        self.book_id = book_id
        self.number = number
        self.is_presented = True

    def __repr__(self):
        return '<Copy of %r' % self.book_id


class UserRole(db.Model):
    __tablename__ = 'users_roles'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), primary_key=True)

    def __init__(self, user_id, role_id):
        self.user_id = user_id
        self.role_id = role_id

    def __repr__(self):
        return '<User %r has role %r' % (self.user_id, self.role_id)


@app.route('/')
@app.route('/index')
def index():
    if not current_user.is_anonymous:
        name = current_user.username
    else:
        name = None
    return render_template('index.html', page_title='Welcome to library', name=name)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    # GET
    if request.method == 'GET':
        return render_template('login.html', form=form, page_title='Log In')

    # POST
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        remember = form.remember.data
        user = User.query.filter_by(username=username).first()
        if user and user.verify_pass(password):
            login_user(user, remember=remember)
            identity = Identity(user.id)
            identity_changed.send(app, identity=identity)
            if admin_perm.can():
                return redirect(url_for('librarian'))
            return redirect(url_for('reader'))
    return abort(401)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        new_user = User(username, email, password)
        present_users = db.session.query(User).filter_by(username=username).count()
        if present_users:
            flash('User exists')
            return render_template('register.html', form=form)
        else:
            db.session.add(new_user)
            db.session.commit()
            db.engine.execute(SET_ROLE.format(username, DEFAULT_ROLE.value))
        return redirect(url_for('login'))
    return render_template('register.html', form=form, page_title='Register')


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()

    # Remove session keys set by Flask-Principal
    for key in ('identity.name', 'identity.auth_type'):
        session.pop(key, None)

    # Tell Flask-Principal the user is anonymous
    # identity_changed.send(app, identity=AnonymousIdentity())
    flash('You have been logged out')
    return redirect(url_for('index'))


@app.route('/librarian', methods=['GET'])
@login_required
@admin_perm.require(http_exception=401)
def librarian():
    return render_template('librarian.html', page_title='Librarian', name=current_user.username)


# @app.route('/reader/<int:id>')
@app.route('/reader', methods=['GET'])
@login_required
def reader():
    return render_template('reader.html', page_title='Reader', name=current_user.username)


# ********************* API *************************** #
# /api/books GET
@app.route('/api/books')
def get_books():
    """
    Get list of present books
    :return: All books
    """
    result = []

    try:
        name = request.args['search']
    except StandardError, err:
        app.logger.warning("get_books()->['search' arg]: " + str(err))
        name = ''

    try:
        limit = int(request.args['pageSz'])
    except StandardError, err:
        app.logger.warning("get_books()->['pageSz' arg]: " + str(err))
        limit = 0

    try:
        page_number = int(request.args['pageNr'])
    except StandardError, err:
        app.logger.warning("get_books()->['pageNr' arg]: " + str(err))
        page_number = 1

    offset = get_offset(limit, page_number)

    if limit == 0:
        limit = 'ALL'

    books = db.engine.execute(GET_BOOKS.format(name, limit, offset))
    for book in books:
        result.append({
            'id': book.id,
            'title': book.title,
            'genre': book.genre,
            'isbn': book.isbn,
            'year': book.year,
            'author': book.author,
            'count': int(book.count)
        })

    return jsonify({'result': result})


# /api/books POST
@app.route('/api/books', methods=['POST'])
@login_required
@admin_perm.require(http_exception=401)
def post_book():
    """
    Create new book
    :return: The result
    """
    try:
        title = request.json['title']
        genre = request.json['genre']
        isbn = request.json['isbn']
        year = int(request.json['year'])
        author = request.json['author']

        book = Book(title, genre, isbn, year, author)
        db.session.add(book)
        db.session.commit()
        return jsonify({'result': 'Book added'})
    except Exception, err:
        app.logger.warning("post_book(): " + str(err))
        return jsonify({'error': 'Wrong request data'})


# /api/books/taken GET
@app.route('/api/books/taken')
@login_required
def get_taken_books():
    """
    Get list of taken books
    :return: All books
    """
    result = []

    try:
        limit = int(request.args['pageSz'])
    except StandardError, err:
        app.logger.warning("get_books()->['pageSz' arg]: " + str(err))
        limit = 0

    try:
        page_number = int(request.args['pageNr'])
    except StandardError, err:
        app.logger.warning("get_books()->['pageNr' arg]: " + str(err))
        page_number = 1

    offset = get_offset(limit, page_number)

    if limit == 0:
        limit = 'ALL'

    name = current_user.username
    copies = db.engine.execute(GET_BOOKS_BY_READER.format(name, limit, offset))
    for copy in copies:
        result.append({
            'book_id': copy.id,
            'title': copy.title,
            'genre': copy.genre,
            'isbn': copy.isbn,
            'year': copy.year,
            'author': copy.author,
            'borrow': copy.borrow_date.strftime(DATE_FORMAT),
            'return': copy.return_date.strftime(DATE_FORMAT),
            'number': copy.number
        })
    return jsonify({'result': result})


# /api/books/all GET
@app.route('/api/books/all')
def get_all_books():
    """
    Get list of all books
    :return: All books
    """
    result = []
    books = db.session.query(Book).all()
    for book in books:
        result.append({
            'id': book.id,
            'title': book.title,
            'genre': book.genre,
            'isbn': book.isbn,
            'year': book.year,
            'author': book.author
        })
    return jsonify({'result': result})


# /api/books/{BOOK} GET
@app.route('/api/books/<isbn>')
@login_required
def get_book(isbn):
    """
    Get particular book
    :param isbn: Books's ISBN
    :return: Result JSON
    """
    book = Book.query.filter_by(isbn=isbn).first()
    if book:
        result = {
            'id': book.id,
            'title': book.title,
            'genre': book.genre,
            'isbn': book.isbn,
            'year': book.year,
            'author': book.author
        }
    else:
        result = None
    return jsonify({'result': result})


# /api/books/{BOOK} PUT
@app.route('/api/books/<isbn>', methods=['PUT'])
@login_required
@admin_perm.require(http_exception=401)
def update_book(isbn):
    """
    Update book by ISBN
    :param isbn: Book's ISBN
    :return: Result
    """
    try:
        db.session.query(Book).filter_by(isbn=isbn).update(request.json)
        db.session.commit()
    except Exception, err:
        app.logger.warning("update_book(): " + str(err))
        return jsonify({'error': 'Wrong request data'})
    return jsonify({'result': 'Book updated'})


# /api/books/{BOOK} DELETE
@app.route('/api/books/<isbn>', methods=['DELETE'])
@login_required
@admin_perm.require(http_exception=401)
def delete_book(isbn):
    """
    Delete book by ISBN
    :param isbn: Book's ISBN
    :return:
    """
    try:
        result = db.session.query(Book).filter_by(isbn=isbn).delete()
        db.session.commit()
    except StandardError, err:
        app.logger.warning("delete_book(): " + str(err))
        return jsonify({'error': 'Wrong request data'})
    if result == 0:
        return jsonify({'error': 'No such item'})
    return jsonify({'result': 'Book deleted'})


# /api/books/{BOOK}/copies GET
@app.route('/api/books/<isbn>/copies')
@login_required
def get_copy(isbn):
    """
    Get book's copies
    :param isbn: ISBN
    :return: Number of copies
    """
    book = db.session.query(Book).filter_by(isbn=isbn).first()
    copies = db.session.query(Copy).filter_by(book_id=book.id).all()
    if copies:
        result = len(copies)
    else:
        result = 0
    return jsonify({'result': result})


# /api/books/{BOOK}/copies POST
@app.route('/api/books/<isbn>/copies', methods=['POST'])
@login_required
@admin_perm.require(http_exception=401)
def post_copy(isbn):
    """
    Add copy by ISBN
    :param isbn: ISBN
    :return: Result
    """
    err_msg = 'Unable to add copy'
    book = db.session.query(Book).filter_by(isbn=isbn).first()
    db.session.flush()
    if book:
        copies = db.session.query(Copy).filter_by(book_id=book.id).all()
        if not copies:
            copy = Copy(book.id, 1)
        else:
            copy = Copy(book.id, len(copies) + 1)
        db.session.add(copy)
        nr = copy.number
        try:
            db.session.commit()
        except exc.SQLAlchemyError:
            return jsonify({'error': err_msg})
        return jsonify({'result': 'Added copy number {0}'.format(nr)})
    return jsonify({'error': err_msg})


# /api/books/{BOOK}/copies/{COPY} GET
@app.route('/api/books/<isbn>/copies/<int:number>')
def get_copy_by_nr(isbn, number):
    """
    Get particular copy by number and book's ISBN'
    :param isbn: ISBN
    :param number: Copy Nr.
    :return: Copy JSON
    """
    book = db.session.query(Book).filter_by(isbn=isbn).first()
    copy = db.session.query(Copy).filter_by(book_id=book.id, number=number).first()
    if copy:
        result = {
            'number': number,
            'title': book.title,
            'genre': book.genre,
            'isbn': isbn,
            'year': book.year,
            'author': book.author
        }
    else:
        result = None
    return jsonify({'result': result})


# /api/books/{BOOK}/copies/{COPY} PUT
@app.route('/api/books/<isbn>/copies/<int:number>', methods=['PUT'])
@login_required
@admin_perm.require(http_exception=401)
def update_copy(isbn, number):
    """
    Update the copy by number and book's ISBN
    :param isbn: Book's ISBN
    :param number: Copy Nr.
    :return: Result
    """
    book = db.session.query(Book).filter_by(isbn=isbn).first()
    copy = db.session.query(Copy).filter_by(book_id=book.id, number=number).first()

    try:
        reader_name = request.json['reader']
        is_presented = request.json['is_presented'] == 'True'
        borrow_date = request.json['borrow_date']
        return_date = request.json['return_date']
        user = db.session.query(User).filter_by(username=reader_name).first()

        reader_id = user.id
        copy_id = copy.id

        values = {
            'reader_id': reader_id,
            'is_presented': is_presented,
            'borrow_date': borrow_date,
            'return_date': return_date,
        }

        db.session.query(Copy).filter_by(id=copy_id).update(values)
    except Exception, err:
        app.logger.warning("update_copy(): " + str(err))
        return jsonify({'error': 'Wrong request data'})
    return jsonify({'result': 'Item successfully updated'})


# /api/books/{BOOK}/copies/{COPY} DELETE
@app.route('/api/books/<isbn>/copies/<int:number>', methods=['DELETE'])
@login_required
@admin_perm.require(http_exception=401)
def delete_copy(isbn, number):
    """
    Delete the copy by ISBN and Nr.
    :param isbn: ISBN
    :param number: Copy Nr.
    :return: Result
    """
    try:
        book = db.session.query(Book).filter_by(isbn=isbn).first()
        copy = db.session.query(Copy).filter_by(book_id=book.id, number=number).first()
        count = db.session.query(Copy).filter_by(id=copy.id).delete()
        db.session.commit()
    except Exception, err:
        app.logger.warning("delete_copy(): " + str(err))
        return jsonify({'error': 'Unable to delete item'})
    return jsonify({'result': '{0} item deleted'.format(count)})


# /api/books/{BOOK}/copies/{COPY}/borrow PUT
@app.route('/api/books/<isbn>/copies/<int:number>/borrow', methods=['PUT'])
@login_required
@admin_perm.require(http_exception=401)
def copy_borrow(isbn, number):
    """
    Borrow the copy from library
    :param isbn: ISBN
    :param number: Copy Nr.
    :return: Result JSON
    """
    try:
        name = request.json['reader']
        user = db.session.query(User).filter_by(username=name).first()
    except Exception, err:
        app.logger.warning("delete_copy(): " + str(err))
        return jsonify({'error': 'Invalid reader username'})

    try:
        book = db.session.query(Book).filter_by(isbn=isbn).first()
        copy = db.session.query(Copy).filter_by(book_id=book.id, number=number).first()
        reader_id = user.id

        date_now = datetime.utcnow()
        borrow_date = date_now.strftime(DATE_FORMAT)
        return_date = date_now + timedelta(days=BORROW_PERIOD)

        values = {
            'reader_id': reader_id,
            'is_presented': False,
            'borrow_date': borrow_date,
            'return_date': return_date,
        }

        db.session.query(Copy).filter_by(id=copy.id).update(values)
    except Exception, err:
        app.logger.warning("copy_borrow(): " + str(err))
        return jsonify({'error': 'Unable to borrow book'})
    return jsonify({'result': 'Book borrowed until {0}'.format(return_date)})


# /api/books/{BOOK}/copies/{COPY}/return PUT
@app.route('/api/books/<isbn>/copies/<int:number>/return', methods=['PUT'])
@login_required
@admin_perm.require(http_exception=401)
def copy_return(isbn, number):
    """
    Return the copy to library
    :param isbn: ISBN
    :param number: Copy Nr.
    :return: Result JSON
    """
    try:
        book = db.session.query(Book).filter_by(isbn=isbn).first()
        copy = db.session.query(Copy).filter_by(book_id=book.id, number=number).first()
    except exc.SQLAlchemyError, err:
        app.logger.warning("copy_return(): " + str(err))
        return jsonify({'error': 'Unable to return book'})

    date_now = datetime.utcnow()

    return_date = date_now.strftime(DATE_FORMAT)

    values = {
        'is_presented': True,
        'return_date': return_date,
    }

    try:
        db.session.query(Copy).filter_by(id=copy.id).update(values)
    except exc.SQLAlchemyError, err:
        app.logger.warning("copy_return(): " + str(err))
        return jsonify({'error': 'Unable to return book'})

    return jsonify({'result': 'Copy returned to library'})


# /api/books/{BOOK}/copies/{COPY}/extend PUT
@app.route('/api/books/<isbn>/copies/<int:number>/extend', methods=['PUT'])
@login_required
def copy_extend(isbn, number):
    """
    Extend the return date of the copy
    :param isbn: ISBN
    :param number: Copy Nr.
    :return: New return date
    """
    book = db.session.query(Book).filter_by(isbn=isbn).first()
    copy = db.session.query(Copy).filter_by(book_id=book.id, number=number).first()

    extend = BORROW_PERIOD
    # new_return_date = datetime.strptime(copy.return_date, DATE_FORMAT) + timedelta(days=extend)
    new_return_date = copy.return_date + timedelta(days=extend)
    values = {
        'return_date': new_return_date,
    }

    db.session.query(Copy).filter_by(id=copy.id).update(values)
    return jsonify({
        'result': 'Return date extended until {0}'.format(new_return_date)
    })


def get_offset(page_size, page_number):
    """
    Calculate offset for pagination
    :param page_size: Limit
    :param page_number: Page Number
    :return:
    """
    return (page_number - 1) * page_size


# *********************************** SEED DATABASE ************************************ #
@app.route('/seed')
def seed_db():
    """
    Seed DB with dummy values
    :return: 'Username:password' tuple list
    """
    result = []

    db.drop_all()
    db.create_all()

    db.session.add(Role('admin'))
    db.session.add(Role('user'))

    for n in range(10):
        username = string.lowercase[n] * 8
        email = "%s@mail.com" % username
        password = str(n) * 8
        result.append((username, password))
        db.session.add(User(username, email, password))
    db.session.commit()

    books = {
        "isbn1": "The Philosopher's Stone",
        "isbn2": "The Chamber of Secrets",
        "isbn3": "The Prisoner of Azkaban",
        "isbn4": "The Goblet of Fire"
    }

    start = 1997

    for book in books:
        isbn = book
        title = books[book]
        genre = "FANTASY"
        year = start
        author = "J.K.ROWLING"
        db.session.add(Book(title, genre, isbn, year, author))
        start += 1
    db.session.commit()

    copies = {
        1: 5,
        2: 7,
        3: 0,
        4: 1
    }

    for copy in copies:
        for n in range(copies[copy]):
            db.session.add(Copy(copy, n + 1))
    db.session.commit()

    for n in range(10):
        db.session.add(UserRole(n + 1, 2))
    db.session.add(UserRole(1, 1))
    db.session.commit()

    return jsonify({'users (1st is admin)': result})


@app.errorhandler(401)
def authentication_failed(e):
    flash('Authenticated failed.')
    return redirect(url_for('login'))


if __name__ == '__main__':
    handler = RotatingFileHandler('application.log', maxBytes=10000, backupCount=1)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.run()
