import os
import secrets
from flask import  render_template, url_for, flash, redirect, request
from SQLgenie import app, db
from SQLgenie.forms import RegistrationForms, LoginForm ,UpdateAccountForm
from SQLgenie.models import User
from flask_login import login_user, current_user, logout_user, login_required


from langchain_community.llms import LlamaCpp
from langchain_core.callbacks import CallbackManager, StreamingStdOutCallbackHandler
from psycopg2 import connect
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain.chains import create_sql_query_chain
from langchain_community.utilities import SQLDatabase
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from operator import itemgetter

callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
# Load the locally downloaded model here
llm = LlamaCpp(
model_path="Mistral-7B-Instruct-SQL-Mistral-7B-Instruct-v0.2-slerp.Q8_0.gguf",
temperature=0.1,
n_ctx=4096,
max_tokens=512,
top_p=1,
n_gpu_layers=35,
callback_manager=callback_manager,
verbose=True
)

@app.route("/")
@app.route("/home")
@login_required
def home():
    return render_template('home.html')

@app.route("/get", methods=["GET", "POST"])
def chat():
    msg = request.form["msg"]
    input = msg
    return get_Chat_response(input)


def get_Chat_response(text):

    lst=text.split()
    if "student" in lst or "class" in lst:
        database="class"
    if "bus" in lst:
        database="bus"
    try:
        dbpg = SQLDatabase.from_uri(
        f"postgresql+psycopg2://postgres:Georgevjoy@localhost:5432/{database}",
        )
    except Exception as e:
        return f"Ask a valid Question!"
    execute_query = QuerySQLDataBaseTool(db=dbpg)
    write_query = create_sql_query_chain(llm, dbpg)
    answer_prompt = PromptTemplate.from_template(
    """ You are a data analyst at a company. You are interacting with a user who is asking you questions about the company's database.
    Based on the user question below, sql query, and sql response, write a Natural Language response.

    SQL Query: <SQL>{query}</SQL>
    User question: {question}
    SQL Response: {result} """
    )
    answer = answer_prompt | llm | StrOutputParser()
    chain = (
        RunnablePassthrough.assign(query=write_query).assign(
        result=itemgetter("query") | execute_query
        )
        | answer
    )
    result=chain.invoke({"question": text})
    return result

@app.route("/about")
def about():
    return render_template('about.html',title='About')

@app.route("/register", methods=['GET','POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForms()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, password=form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('your account has been created! You are now able to log in','success')
        return redirect(url_for('login'))
    return render_template('register2.html',title='Login',form=form)
    
@app.route("/login", methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.password==form.password.data:
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login unsuccessful.Please check username and password','danger')
    return render_template('login.html', title='Login', form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)
    form_picture.save(picture_path)

    return picture_fn



@app.route("/account", methods=['GET','POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file= save_picture(form.picture.data)
            current_user.image_file = picture_file

        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('your account has been update!','success' )
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email

    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account', image_file=image_file ,form=form)
