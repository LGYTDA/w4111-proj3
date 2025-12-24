
"""
Columbia's COMS W4111.001 Introduction to Databases
Example Webserver
To run locally:
    python server.py
Go to http://localhost:8111 in your browser.
A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""
import os
import time
  # accessible as a variable in index.html:
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, url_for, session

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
app.secret_key = 'academic_research_platform_key'  # Secret key for sessions


#
# The following is a dummy URI that does not connect to a valid database. You will need to modify it to connect to your Part 2 database in order to use the data.
#
# XXX: The URI should be in the format of:
#
#     postgresql://USER:PASSWORD@34.148.223.31/proj1part2
#
# For example, if you had username zy2431 and password 123123, then the following line would be:
#
#     DATABASEURI = "postgresql://zy2431:123123@34.148.223.31/proj1part2"
#
# Modify these with your own credentials you received from TA!
DATABASE_USERNAME = "lgy2104"
DATABASE_PASSWRD = "15Sihamrocks"
DATABASE_HOST = "34.148.223.31"
DATABASEURI = f"postgresql://lgy2104:15Sihamrocks@34.148.223.31/proj1part2"


#
# This line creates a database engine that knows how to connect to the URI above.
#
engine = create_engine(DATABASEURI)

@app.before_request
def before_request():
	"""
	This function is run at the beginning of every web request
	(every time you enter an address in the web browser).
	We use it to setup a database connection that can be used throughout the request.

	The variable g is globally accessible.
	"""
	try:
		g.conn = engine.connect()
	except:
		print("uh oh, problem connecting to database")
		import traceback; traceback.print_exc()
		g.conn = None

@app.teardown_request
def teardown_request(exception):
	"""
	At the end of the web request, this makes sure to close the database connection.
	If you don't, the database could run out of memory!
	"""
	try:
		g.conn.close()
	except Exception as e:
		pass

#HELPER FUNCTIONS
def get_all_departments():
    cursor = g.conn.execute(text("SELECT dept_id, dept_name, university_name FROM Department ORDER BY dept_name"))
    departments = []
    for result in cursor:
        departments.append({
            'dept_id': result[0],
            'dept_name': result[1],
            'university_name': result[2]
        })
    cursor.close()
    return departments

def get_all_skills():
    """Get all unique skills without duplicating by proficiency level"""
    cursor = g.conn.execute(text("""
        SELECT DISTINCT ON (skill_name) skill_id, skill_name
        FROM Skill
        ORDER BY skill_name, skill_id
    """))

    skills = []
    for result in cursor:
        skills.append({
            'skill_id': result[0],
            'skill_name': result[1]
        })
    cursor.close()

    return skills

def get_skill_with_proficiency(skill_name, proficiency_level):
    """Get the specific skill_id for a skill name and proficiency level"""
    cursor = g.conn.execute(text("""
        SELECT skill_id FROM Skill
        WHERE skill_name = :skill_name AND proficiency_level = :proficiency_level
    """), {
        "skill_name": skill_name,
        "proficiency_level": proficiency_level
    })
    result = cursor.fetchone()
    cursor.close()

    return result[0] if result else None

def get_all_universities():
    cursor = g.conn.execute(text("SELECT university_name FROM University ORDER BY university_name"))
    universities = []
    for result in cursor:
        universities.append(result[0])
    cursor.close()
    return universities

#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to, for example, localhost:8111/foobar/ with POST or GET then you could use:
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
#
# see for routing: https://flask.palletsprojects.com/en/1.1.x/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#

#CHOOSING AND CHANGING USER
@app.route('/')
def entry():
    # Clear any existing role
    if 'role' in session:
        session.pop('role')
    return render_template('entry.html')
@app.route('/set_role', methods=['POST'])
def set_role():
    role = request.form.get('role')
    if role in ['student', 'professor']:
        session['role'] = role
    return redirect(url_for('index'))
@app.route('/change_role')
def change_role():
    # Clear the current role
    if 'role' in session:
        session.pop('role')

    # Redirect back to the role selection page
    return redirect(url_for('entry'))

#PAGES
@app.route('/welcome')
def index():
	"""
	request is a special object that Flask provides to access web request information:

	request.method:   "GET" or "POST"
	request.form:     if the browser submitted a form, this contains the data in the form
	request.args:     dictionary of URL arguments, e.g., {a:1, b:2} for http://localhost?a=1&b=2

	See its API: https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data
	"""

	cursor_students = g.conn.execute(text("SELECT COUNT(*) FROM Student"))
	count_students = cursor_students.fetchone()[0]
	cursor_students.close()

	cursor_professors = g.conn.execute(text("SELECT COUNT(*) FROM Professor"))
	count_professors = cursor_professors.fetchone()[0]
	cursor_professors.close()

	cursor_projects = g.conn.execute(text("SELECT COUNT(*) FROM Project"))
	count_projects = cursor_projects.fetchone()[0]
	cursor_projects.close()

	# Get some recent projects
	cursor_recent_projects = g.conn.execute(text("""
	    SELECT p.project_id, p.title, p.status, p.start_date, pr.name
	    FROM Project p
	    JOIN Leads_Project lp ON p.project_id = lp.project_id
	    JOIN Professor pr ON lp.staff_id = pr.staff_id
	    ORDER BY p.start_date DESC
	    LIMIT 3
	"""))

	recent_projects = []
	for result in cursor_recent_projects:
	    recent_projects.append({
	        'project_id': result[0],
	        'title': result[1],
	        'status': result[2],
	        'start_date': result[3],
	        'professor_name': result[4]
	    })
	cursor_recent_projects.close()

	context = {
	    'count_students': count_students,
	    'count_professors': count_professors,
	    'count_projects': count_projects,
	    'recent_projects': recent_projects
	}

	return render_template("index.html", **context)

# Students routes
@app.route('/students')
def all_students():
    cursor = g.conn.execute(text("""
        SELECT s.student_id, s.name, s.email_addr, s.academic_level, s.year_of_study, p.name as advisor_name
        FROM Student s
        LEFT JOIN Professor p ON s.staff_id = p.staff_id
        ORDER BY s.name
    """))

    students = []
    for result in cursor:
        students.append({
            'student_id': result[0],
            'name': result[1],
            'email': result[2],
            'academic_level': result[3],
            'year_of_study': result[4],
            'advisor_name': result[5]
        })
    cursor.close()

    return render_template("students/all.html", students=students)

#viewing details of each student
@app.route('/students/<student_id>')
def student_profile(student_id):
    cursor = g.conn.execute(text("""
        SELECT s.student_id, s.name, s.email_addr, s.academic_level, s.year_of_study,
               p.staff_id, p.name as advisor_name
        FROM Student s
        LEFT JOIN Professor p ON s.staff_id = p.staff_id
        WHERE s.student_id = :student_id
    """), {'student_id': student_id})

    student = cursor.fetchone()
    if not student:
        return "Student not found", 404

    student_info = {
        'student_id': student[0],
        'name': student[1],
        'email': student[2],
        'academic_level': student[3],
        'year_of_study': student[4],
        'advisor_id': student[5],
        'advisor_name': student[6]
    }
    cursor.close()

    # Get student's department
    cursor = g.conn.execute(text("""
        SELECT d.dept_id, d.dept_name, d.university_name
        FROM Part_Of po
        JOIN Department d ON po.dept_id = d.dept_id AND po.university_name = d.university_name
        WHERE po.student_id = :student_id
    """), {'student_id': student_id})

    departments = []
    for result in cursor:
        departments.append({
            'dept_id': result[0],
            'dept_name': result[1],
            'university_name': result[2]
        })
    cursor.close()

    # Get student's skills
    cursor = g.conn.execute(text("""
        SELECT s.skill_id, s.skill_name, s.proficiency_level
        FROM Has_Skill hs
        JOIN Skill s ON hs.skill_id = s.skill_id
        WHERE hs.student_id = :student_id
    """), {'student_id': student_id})

    skills = []
    for result in cursor:
        skills.append({
            'skill_id': result[0],
            'skill_name': result[1],
            'proficiency_level': result[2]
        })
    cursor.close()

    # Get projects the student has applied to
    cursor = g.conn.execute(text("""
        SELECT p.project_id, p.title, p.status, p.start_date, pr.name as professor_name
        FROM Applies_To_Project ap
        JOIN Project p ON ap.project_id = p.project_id
        JOIN Leads_Project lp ON p.project_id = lp.project_id
        JOIN Professor pr ON lp.staff_id = pr.staff_id
        WHERE ap.student_id = :student_id
    """), {'student_id': student_id})

    applied_projects = []
    for result in cursor:
        applied_projects.append({
            'project_id': result[0],
            'title': result[1],
            'status': result[2],
            'start_date': result[3],
            'professor_name': result[4]
        })
    cursor.close()

    return render_template("students/profile.html",
                          student=student_info,
                          departments=departments,
                          skills=skills,
                          applied_projects=applied_projects)

@app.route('/students/add', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        # Generate next student ID
        cursor = g.conn.execute(text("SELECT student_id FROM Student ORDER BY student_id DESC LIMIT 1"))
        result = cursor.fetchone()
        cursor.close()

        if result:
            last_id = result[0]
            # Extract numeric part and increment
            numeric_part = int(last_id[1:])
            next_numeric = numeric_part + 1
            student_id = f"S{next_numeric:03d}"  # Format with leading zeros (e.g., S002, S003)
        else:
            # If no existing students, start with S001
            student_id = "S001"

        # Get form data (student_id is now generated)
        name = request.form['name']
        email_addr = request.form['email_addr']
        academic_level = request.form['academic_level']
        year_of_study = request.form['year_of_study']
        staff_id = request.form['staff_id'] if request.form['staff_id'] else None

        # Insert student
        params = {
            "student_id": student_id,
            "name": name,
            "email_addr": email_addr,
            "academic_level": academic_level,
            "year_of_study": year_of_study,
            "staff_id": staff_id
        }

        try:
            g.conn.execute(text("""
                INSERT INTO Student (student_id, name, email_addr, academic_level, year_of_study, staff_id)
                VALUES (:student_id, :name, :email_addr, :academic_level, :year_of_study, :staff_id)
            """), params)

            # If department is selected, add to Part_Of
            if 'dept_id' in request.form and request.form['dept_id']:
                dept_parts = request.form['dept_id'].split('|')
                if len(dept_parts) == 2:
                    dept_id, university_name = dept_parts
                    g.conn.execute(text("""
                        INSERT INTO Part_Of (student_id, dept_id, university_name)
                        VALUES (:student_id, :dept_id, :university_name)
                    """), {
                        "student_id": student_id,
                        "dept_id": dept_id,
                        "university_name": university_name
                    })

            # Process selected existing skills with proficiency levels
            if 'skill_ids[]' in request.form:
                skill_ids = request.form.getlist('skill_ids[]')
                proficiency_levels = request.form.getlist('proficiency_levels[]')

                for i in range(len(skill_ids)):
                    if skill_ids[i] and proficiency_levels[i]:  # Only process if both are selected
                        # Get the skill name from the selected skill_id
                        cursor = g.conn.execute(text("""
                            SELECT skill_name FROM Skill WHERE skill_id = :skill_id
                        """), {"skill_id": skill_ids[i]})
                        skill_result = cursor.fetchone()
                        cursor.close()

                        if skill_result:
                            skill_name = skill_result[0]

                            # Find the specific skill_id with the correct name and proficiency level
                            cursor = g.conn.execute(text("""
                                SELECT skill_id FROM Skill
                                WHERE skill_name = :skill_name AND proficiency_level = :proficiency_level
                            """), {
                                "skill_name": skill_name,
                                "proficiency_level": proficiency_levels[i]
                            })
                            matching_skill = cursor.fetchone()
                            cursor.close()

                            if matching_skill:
                                # Insert into Has_Skill with the matched skill_id
                                g.conn.execute(text("""
                                    INSERT INTO Has_Skill (student_id, skill_id)
                                    VALUES (:student_id, :skill_id)
                                """), {
                                    "student_id": student_id,
                                    "skill_id": matching_skill[0]
                                })

            # Process new custom skills
            if 'new_skill_names[]' in request.form:
                new_skill_names = request.form.getlist('new_skill_names[]')
                new_skill_proficiencies = request.form.getlist('new_skill_proficiencies[]')

                for i in range(len(new_skill_names)):
                    if new_skill_names[i] and new_skill_proficiencies[i]:  # Only process if both are provided
                        # Generate a new skill_id
                        cursor = g.conn.execute(text("SELECT skill_id FROM Skill ORDER BY skill_id DESC LIMIT 1"))
                        skill_result = cursor.fetchone()
                        cursor.close()

                        if skill_result:
                            last_skill_id = skill_result[0]
                            # Extract numeric part and increment
                            numeric_part = int(last_skill_id[2:])
                            next_numeric = numeric_part + 1
                            new_skill_id = f"SK{next_numeric:03d}"  # Format with leading zeros (e.g., SK002)
                        else:
                            # If no existing skills, start with SK001
                            new_skill_id = "SK001"

                        # Insert the new skill
                        g.conn.execute(text("""
                            INSERT INTO Skill (skill_id, skill_name, proficiency_level)
                            VALUES (:skill_id, :skill_name, :proficiency_level)
                        """), {
                            "skill_id": new_skill_id,
                            "skill_name": new_skill_names[i],
                            "proficiency_level": new_skill_proficiencies[i]
                        })

                        # Associate the new skill with the student
                        g.conn.execute(text("""
                            INSERT INTO Has_Skill (student_id, skill_id)
                            VALUES (:student_id, :skill_id)
                        """), {
                            "student_id": student_id,
                            "skill_id": new_skill_id
                        })

            return redirect(url_for('student_profile', student_id=student_id))
        except Exception as e:
            return f"Error adding student: {str(e)}"

    # GET request - render the form
    # Get all professors for advisor selection
    cursor = g.conn.execute(text("SELECT staff_id, name FROM Professor ORDER BY name"))
    professors = []
    for result in cursor:
        professors.append({
            'staff_id': result[0],
            'name': result[1]
        })
    cursor.close()

    # Get all departments
    departments = get_all_departments()

    # Get all unique skills (without duplicates for different proficiency levels)
    cursor = g.conn.execute(text("""
        SELECT DISTINCT ON (skill_name) skill_id, skill_name
        FROM Skill
        ORDER BY skill_name
    """))
    skills = []
    for result in cursor:
        skills.append({
            'skill_name': result[1],
            'skill_id': result[0]
        })
    cursor.close()

    return render_template("students/add.html", professors=professors, departments=departments, skills=skills)

@app.route('/students/<student_id>/edit', methods=['GET', 'POST'])
def edit_student(student_id):
    if request.method == 'POST':
        # Get form data
        name = request.form['name']
        email_addr = request.form['email_addr']
        academic_level = request.form['academic_level']
        year_of_study = request.form['year_of_study']
        staff_id = request.form['staff_id'] if request.form['staff_id'] else None

        # Update student
        params = {
            "student_id": student_id,
            "name": name,
            "email_addr": email_addr,
            "academic_level": academic_level,
            "year_of_study": year_of_study,
            "staff_id": staff_id
        }

        try:
            g.conn.execute(text("""
                UPDATE Student
                SET name = :name, email_addr = :email_addr, academic_level = :academic_level,
                    year_of_study = :year_of_study, staff_id = :staff_id
                WHERE student_id = :student_id
            """), params)

            # If department is selected, update Part_Of
            if 'dept_id' in request.form and request.form['dept_id']:
                # First delete existing department affiliations
                g.conn.execute(text("""
                    DELETE FROM Part_Of WHERE student_id = :student_id
                """), {"student_id": student_id})

                # Then add new department
                dept_parts = request.form['dept_id'].split('|')
                if len(dept_parts) == 2:
                    dept_id, university_name = dept_parts
                    g.conn.execute(text("""
                        INSERT INTO Part_Of (student_id, dept_id, university_name)
                        VALUES (:student_id, :dept_id, :university_name)
                    """), {
                        "student_id": student_id,
                        "dept_id": dept_id,
                        "university_name": university_name
                    })

            # Handle skills updates - start by removing all existing skills
            g.conn.execute(text("""
                DELETE FROM Has_Skill WHERE student_id = :student_id
            """), {"student_id": student_id})

            # Add the new skills from existing skills, using the same approach as add_student
            if 'skill_ids[]' in request.form:
                skill_ids = request.form.getlist('skill_ids[]')
                proficiency_levels = request.form.getlist('proficiency_levels[]')

                for i in range(len(skill_ids)):
                    if skill_ids[i] and proficiency_levels[i]:  # Only process if both are selected
                        # Get the skill name from the selected skill_id
                        cursor = g.conn.execute(text("""
                            SELECT skill_name FROM Skill WHERE skill_id = :skill_id
                        """), {"skill_id": skill_ids[i]})
                        skill_result = cursor.fetchone()
                        cursor.close()

                        if skill_result:
                            skill_name = skill_result[0]

                            # Find the specific skill_id with the correct name and proficiency level
                            cursor = g.conn.execute(text("""
                                SELECT skill_id FROM Skill
                                WHERE skill_name = :skill_name AND proficiency_level = :proficiency_level
                            """), {
                                "skill_name": skill_name,
                                "proficiency_level": proficiency_levels[i]
                            })
                            matching_skill = cursor.fetchone()
                            cursor.close()

                            if matching_skill:
                                # Insert into Has_Skill with the matched skill_id
                                g.conn.execute(text("""
                                    INSERT INTO Has_Skill (student_id, skill_id)
                                    VALUES (:student_id, :skill_id)
                                """), {
                                    "student_id": student_id,
                                    "skill_id": matching_skill[0]
                                })

            # Process new custom skills
            if 'new_skill_names[]' in request.form:
                new_skill_names = request.form.getlist('new_skill_names[]')
                new_skill_proficiencies = request.form.getlist('new_skill_proficiencies[]')

                for i in range(len(new_skill_names)):
                    if new_skill_names[i] and new_skill_proficiencies[i]:  # Only process if both are provided
                        # Generate a new skill_id
                        cursor = g.conn.execute(text("SELECT skill_id FROM Skill ORDER BY skill_id DESC LIMIT 1"))
                        skill_result = cursor.fetchone()
                        cursor.close()

                        if skill_result:
                            last_skill_id = skill_result[0]
                            # Extract numeric part and increment
                            numeric_part = int(last_skill_id[2:])
                            next_numeric = numeric_part + 1
                            new_skill_id = f"SK{next_numeric:03d}"  # Format with leading zeros (e.g., SK002)
                        else:
                            # If no existing skills, start with SK001
                            new_skill_id = "SK001"

                        # Insert the new skill
                        g.conn.execute(text("""
                            INSERT INTO Skill (skill_id, skill_name, proficiency_level)
                            VALUES (:skill_id, :skill_name, :proficiency_level)
                        """), {
                            "skill_id": new_skill_id,
                            "skill_name": new_skill_names[i],
                            "proficiency_level": new_skill_proficiencies[i]
                        })

                        # Associate the new skill with the student
                        g.conn.execute(text("""
                            INSERT INTO Has_Skill (student_id, skill_id)
                            VALUES (:student_id, :skill_id)
                        """), {
                            "student_id": student_id,
                            "skill_id": new_skill_id
                        })

            return redirect(url_for('student_profile', student_id=student_id))
        except Exception as e:
            return f"Error updating student: {str(e)}"

    # GET request - Retrieve student info
    cursor = g.conn.execute(text("""
        SELECT s.student_id, s.name, s.email_addr, s.academic_level, s.year_of_study, s.staff_id
        FROM Student s
        WHERE s.student_id = :student_id
    """), {'student_id': student_id})

    student = cursor.fetchone()
    if not student:
        return "Student not found", 404

    student_info = {
        'student_id': student[0],
        'name': student[1],
        'email_addr': student[2],
        'academic_level': student[3],
        'year_of_study': student[4],
        'staff_id': student[5]
    }
    cursor.close()

    # Get all professors for advisor selection
    cursor = g.conn.execute(text("SELECT staff_id, name FROM Professor ORDER BY name"))
    professors = []
    for result in cursor:
        professors.append({
            'staff_id': result[0],
            'name': result[1]
        })
    cursor.close()

    # Get student's current department
    cursor = g.conn.execute(text("""
        SELECT d.dept_id, d.dept_name, d.university_name
        FROM Part_Of po
        JOIN Department d ON po.dept_id = d.dept_id AND po.university_name = d.university_name
        WHERE po.student_id = :student_id
    """), {'student_id': student_id})

    current_dept = cursor.fetchone()
    current_dept_value = None
    if current_dept:
        current_dept_value = f"{current_dept[0]}|{current_dept[2]}"
    cursor.close()

    # Use get_all_departments() helper function
    departments = get_all_departments()

    # Get all unique skills (without fetching student's current skills)
    cursor = g.conn.execute(text("""
        SELECT DISTINCT ON (skill_name) skill_id, skill_name
        FROM Skill
        ORDER BY skill_name
    """))
    skills = []
    for result in cursor:
        skills.append({
            'skill_id': result[0],
            'skill_name': result[1]
        })
    cursor.close()

    return render_template("students/edit.html",
                          student=student_info,
                          professors=professors,
                          departments=departments,
                          current_dept_value=current_dept_value,
                          skills=skills)  # No student_skills parameter now

#PROFESSORS
@app.route('/professors')
def all_professors():
    cursor = g.conn.execute(text("""
        SELECT p.staff_id, p.name, p.email_addr, p.research_focus,
               (SELECT COUNT(*) FROM Leads_Project lp WHERE lp.staff_id = p.staff_id) as project_count
        FROM Professor p
        ORDER BY p.name
    """))

    professors = []
    for result in cursor:
        professors.append({
            'staff_id': result[0],
            'name': result[1],
            'email': result[2],
            'research_focus': result[3],
            'project_count': result[4]
        })
    cursor.close()

    return render_template("professors/all.html", professors=professors)

#prof profile view
@app.route('/professors/<staff_id>')
def professor_profile(staff_id):
    # Get professor info
    cursor = g.conn.execute(text("""
        SELECT staff_id, name, email_addr, research_focus
        FROM Professor
        WHERE staff_id = :staff_id
    """), {'staff_id': staff_id})

    professor = cursor.fetchone()
    if not professor:
        return "Professor not found", 404

    professor_info = {
        'staff_id': professor[0],
        'name': professor[1],
        'email': professor[2],
        'research_focus': professor[3]
    }
    cursor.close()

    # Get professor's department and university
    cursor = g.conn.execute(text("""
        SELECT d.dept_id, d.dept_name, d.university_name
        FROM Researches_At ra
        JOIN Department d ON ra.dept_id = d.dept_id AND ra.university_name = d.university_name
        WHERE ra.staff_id = :staff_id
    """), {'staff_id': staff_id})

    departments = []
    for result in cursor:
        departments.append({
            'dept_id': result[0],
            'dept_name': result[1],
            'university_name': result[2]
        })
    cursor.close()

    # Get projects led by professor
    cursor = g.conn.execute(text("""
        SELECT p.project_id, p.title, p.abstract, p.status, p.start_date,
               (SELECT COUNT(*) FROM Applies_To_Project ap WHERE ap.project_id = p.project_id) as applicant_count
        FROM Leads_Project lp
        JOIN Project p ON lp.project_id = p.project_id
        WHERE lp.staff_id = :staff_id
        ORDER BY p.start_date DESC
    """), {'staff_id': staff_id})

    projects = []
    for result in cursor:
        # Format the date if it's a datetime object
        start_date = result[4]
        if start_date:
            if hasattr(start_date, 'strftime'):
                start_date = start_date.strftime('%Y-%m-%d')

        projects.append({
            'project_id': result[0],
            'title': result[1],
            'abstract': result[2],
            'status': result[3],
            'start_date': start_date,
            'applicant_count': result[5]
        })
    cursor.close()

    # Get students advised by professor
    cursor = g.conn.execute(text("""
        SELECT student_id, name, academic_level, year_of_study
        FROM Student
        WHERE staff_id = :staff_id
        ORDER BY name
    """), {'staff_id': staff_id})

    students = []
    for result in cursor:
        students.append({
            'student_id': result[0],
            'name': result[1],
            'academic_level': result[2],
            'year_of_study': result[3]
        })
    cursor.close()

    return render_template("professors/profile.html",
                           professor=professor_info,
                           departments=departments,
                           projects=projects,
                           students=students)


@app.route('/professors/add', methods=['GET', 'POST'])
def add_professor():
    if request.method == 'POST':
        # Get form data
        name = request.form['name']
        email = request.form['email']
        research_focus = request.form['research_focus']

        # Generate new staff_id using a more robust method
        try:
            # Get all existing professor IDs
            result = g.conn.execute(text("SELECT staff_id FROM Professor"))
            existing_ids = [row[0] for row in result]

            # Extract numeric parts from P-prefixed IDs
            p_numbers = []
            for id in existing_ids:
                if id.startswith('P') and id[1:].isdigit():
                    p_numbers.append(int(id[1:]))

            # If we found any valid P-format numbers, use the next one
            if p_numbers:
                next_number = max(p_numbers) + 1
                staff_id = f"P{next_number:03d}"  # Format with leading zeros
            else:
                # No existing P-format IDs
                staff_id = "P001"

        except Exception as e:
            # Fallback in case of database error
            import time
            staff_id = f"P{int(time.time() % 10000)}"

        # Insert professor
        params = {
            "staff_id": staff_id,
            "name": name,
            "email": email,
            "research_focus": research_focus
        }

        try:
            g.conn.execute(text("""
                INSERT INTO Professor (staff_id, name, email_addr, research_focus)
                VALUES (:staff_id, :name, :email, :research_focus)
            """), params)

            # If department is selected, add to Researches_At
            if 'dept_id' in request.form and request.form['dept_id']:
                dept_parts = request.form['dept_id'].split('|')
                if len(dept_parts) == 2:
                    dept_id, university_name = dept_parts
                    g.conn.execute(text("""
                        INSERT INTO Researches_At (staff_id, dept_id, university_name)
                        VALUES (:staff_id, :dept_id, :university_name)
                    """), {
                        "staff_id": staff_id,
                        "dept_id": dept_id,
                        "university_name": university_name
                    })

            return redirect(url_for('professor_profile', staff_id=staff_id))
        except Exception as e:
            return f"Error adding professor: {str(e)}"

    # Get all departments
    departments = get_all_departments()

    return render_template("professors/add.html", departments=departments)


@app.route('/professors/<staff_id>/edit', methods=['GET', 'POST'])
def edit_professor(staff_id):
    if request.method == 'POST':
        # Get form data
        name = request.form['name']
        email = request.form['email']
        research_focus = request.form['research_focus']

        # Update professor
        params = {
            "staff_id": staff_id,
            "name": name,
            "email": email,
            "research_focus": research_focus
        }

        try:
            g.conn.execute(text("""
                UPDATE Professor
                SET name = :name, email_addr = :email, research_focus = :research_focus
                WHERE staff_id = :staff_id
            """), params)
            #g.conn.commit()

            # If department is selected, update Researches_At
            if 'dept_id' in request.form and request.form['dept_id']:
                # First delete existing department affiliations
                g.conn.execute(text("""
                    DELETE FROM Researches_At WHERE staff_id = :staff_id
                """), {"staff_id": staff_id})
                #g.conn.commit()

                # Then add new department
                dept_parts = request.form['dept_id'].split('|')
                if len(dept_parts) == 2:
                    dept_id, university_name = dept_parts
                    g.conn.execute(text("""
                        INSERT INTO Researches_At (staff_id, dept_id, university_name)
                        VALUES (:staff_id, :dept_id, :university_name)
                    """), {
                        "staff_id": staff_id,
                        "dept_id": dept_id,
                        "university_name": university_name
                    })
                    #g.conn.commit()

            return redirect(url_for('professor_profile', staff_id=staff_id))
        except Exception as e:
            return f"Error updating professor: {str(e)}"

    # Get professor info
    cursor = g.conn.execute(text("""
        SELECT staff_id, name, email_addr, research_focus
        FROM Professor
        WHERE staff_id = :staff_id
    """), {'staff_id': staff_id})

    professor = cursor.fetchone()
    if not professor:
        return "Professor not found", 404

    professor_info = {
        'staff_id': professor[0],
        'name': professor[1],
        'email': professor[2],
        'research_focus': professor[3]
    }
    cursor.close()

    # Get professor's current department
    cursor = g.conn.execute(text("""
        SELECT d.dept_id, d.dept_name, d.university_name
        FROM Researches_At ra
        JOIN Department d ON ra.dept_id = d.dept_id AND ra.university_name = d.university_name
        WHERE ra.staff_id = :staff_id
    """), {'staff_id': staff_id})

    current_dept = cursor.fetchone()
    current_dept_value = None
    if current_dept:
        current_dept_value = f"{current_dept[0]}|{current_dept[2]}"
    cursor.close()

    # Get all departments
    departments = get_all_departments()

    return render_template("professors/edit.html",
                          professor=professor_info,
                          departments=departments,
                          current_dept_value=current_dept_value)

#PROJECTS
@app.route('/projects')
def all_projects():
    cursor = g.conn.execute(text("""
        SELECT p.project_id, p.title, p.status, p.start_date, pr.name as professor_name,
               (SELECT COUNT(*) FROM Applies_To_Project ap WHERE ap.project_id = p.project_id) as applicant_count
        FROM Project p
        JOIN Leads_Project lp ON p.project_id = lp.project_id
        JOIN Professor pr ON lp.staff_id = pr.staff_id
        ORDER BY p.start_date DESC
    """))

    projects = []
    for result in cursor:
        projects.append({
            'project_id': result[0],
            'title': result[1],
            'status': result[2],
            'start_date': result[3],
            'professor_name': result[4],
            'applicant_count': result[5]
        })
    cursor.close()

    return render_template("projects/all.html", projects=projects)

@app.route('/projects/<project_id>')
def view_project(project_id):
    # Get project info
    cursor = g.conn.execute(text("""
        SELECT p.project_id, p.title, p.abstract, p.status, p.start_date,
               pr.staff_id, pr.name as professor_name
        FROM Project p
        JOIN Leads_Project lp ON p.project_id = lp.project_id
        JOIN Professor pr ON lp.staff_id = pr.staff_id
        WHERE p.project_id = :project_id
    """), {'project_id': project_id})

    project = cursor.fetchone()
    if not project:
        return "Project not found", 404

    project_info = {
        'project_id': project[0],
        'title': project[1],
        'abstract': project[2],
        'status': project[3],
        'start_date': project[4],
        'staff_id': project[5],
        'professor_name': project[6]
    }
    cursor.close()

    # Get required skills
    cursor = g.conn.execute(text("""
        SELECT s.skill_id, s.skill_name, s.proficiency_level
        FROM Requires_Skill rs
        JOIN Skill s ON rs.skill_id = s.skill_id
        WHERE rs.project_id = :project_id
    """), {'project_id': project_id})

    required_skills = []
    for result in cursor:
        required_skills.append({
            'skill_id': result[0],
            'skill_name': result[1],
            'proficiency_level': result[2]
        })
    cursor.close()

    # Get students who applied to this project
    cursor = g.conn.execute(text("""
        SELECT s.student_id, s.name, s.academic_level, s.year_of_study
        FROM Student s
        JOIN Applies_To_Project ap ON s.student_id = ap.student_id
        WHERE ap.project_id = :project_id
    """), {'project_id': project_id})

    applied_students = []
    for result in cursor:
        applied_students.append({
            'student_id': result[0],
            'name': result[1],
            'academic_level': result[2],
            'year_of_study': result[3]
        })
    cursor.close()

    return render_template('projects/project_details.html',
                           project=project_info,
                           skills=required_skills,
                           applied_students=applied_students)

@app.route('/projects/add', methods=['GET', 'POST'])
def add_project():
    if request.method == 'POST':
        # Get form data
        title = request.form['title']
        abstract = request.form['abstract']
        status = request.form['status']
        start_date = request.form['start_date']
        staff_id = request.form['staff_id']  # Professor leading the project

        try:
            # Get the latest project_id
            cursor = g.conn.execute(text("SELECT project_id FROM Project ORDER BY project_id DESC LIMIT 1"))
            result = cursor.fetchone()
            cursor.close()

            if result is None:
                # No projects exist yet, create the first ID
                project_id = "PRJ001"
            else:
                last_id = result[0]
                # Extract the prefix (letters) and the numeric part
                prefix = ''.join(c for c in last_id if c.isalpha())
                numeric_part = ''.join(c for c in last_id if c.isdigit())

                if not numeric_part:
                    # Handle case where there's no number in the ID
                    project_id = f"{prefix}001"
                else:
                    # Increment the numeric part and maintain leading zeros
                    next_num = int(numeric_part) + 1
                    # Format to keep the same number of digits with leading zeros
                    next_num_str = str(next_num).zfill(len(numeric_part))
                    project_id = f"{prefix}{next_num_str}"

            # Insert project
            params = {
                "project_id": project_id,
                "title": title,
                "abstract": abstract,
                "status": status,
                "start_date": start_date
            }

            # Insert into Project table
            g.conn.execute(text("""
                INSERT INTO Project (project_id, title, abstract, status, start_date)
                VALUES (:project_id, :title, :abstract, :status, :start_date)
            """), params)

            # Insert into Leads_Project table to associate with professor
            g.conn.execute(text("""
                INSERT INTO Leads_Project (staff_id, project_id)
                VALUES (:staff_id, :project_id)
            """), {
                "staff_id": staff_id,
                "project_id": project_id
            })

            # If skills are selected, add to Requires_Skill
            if 'skills' in request.form:
                skills = request.form.getlist('skills')
                for skill_id in skills:
                    g.conn.execute(text("""
                        INSERT INTO Requires_Skill (project_id, skill_id)
                        VALUES (:project_id, :skill_id)
                    """), {
                        "project_id": project_id,
                        "skill_id": skill_id
                    })

            return redirect(url_for('view_project', project_id=project_id))
        except Exception as e:
            return f"Error adding project: {str(e)}"

    # Get all professors for project lead selection
    cursor = g.conn.execute(text("SELECT staff_id, name FROM Professor ORDER BY name"))
    professors = []
    for result in cursor:
        professors.append({
            'staff_id': result[0],
            'name': result[1]
        })
    cursor.close()

    # Get all skills
    skills = get_all_skills()

    return render_template("projects/add.html", professors=professors, skills=skills)

@app.route('/projects/<project_id>/edit', methods=['GET', 'POST'])
def edit_project(project_id):
    if request.method == 'POST':
        # Get form data
        title = request.form['title']
        abstract = request.form['abstract']
        status = request.form['status']
        start_date = request.form['start_date']
        staff_id = request.form['staff_id']

        # Update project
        params = {
            "project_id": project_id,
            "title": title,
            "abstract": abstract,
            "status": status,
            "start_date": start_date
        }

        try:
            # Update Project table
            g.conn.execute(text("""
                UPDATE Project
                SET title = :title, abstract = :abstract, status = :status, start_date = :start_date
                WHERE project_id = :project_id
            """), params)

            # Update project lead if changed
            g.conn.execute(text("""
                UPDATE Leads_Project
                SET staff_id = :staff_id
                WHERE project_id = :project_id
            """), {
                "staff_id": staff_id,
                "project_id": project_id
            })

            # Update required skills
            # First, delete existing skill requirements
            g.conn.execute(text("""
                DELETE FROM Requires_Skill WHERE project_id = :project_id
            """), {"project_id": project_id})

            # Then add new skills if selected
            if 'skills' in request.form:
                skills = request.form.getlist('skills')
                for skill_id in skills:
                    g.conn.execute(text("""
                        INSERT INTO Requires_Skill (project_id, skill_id)
                        VALUES (:project_id, :skill_id)
                    """), {
                        "project_id": project_id,
                        "skill_id": skill_id
                    })

            return redirect(url_for('view_project', project_id=project_id))
        except Exception as e:
            return f"Error updating project: {str(e)}"

    # Get project info
    cursor = g.conn.execute(text("""
        SELECT p.project_id, p.title, p.abstract, p.status, p.start_date, lp.staff_id
        FROM Project p
        JOIN Leads_Project lp ON p.project_id = lp.project_id
        WHERE p.project_id = :project_id
    """), {'project_id': project_id})

    project = cursor.fetchone()
    if not project:
        return "Project not found", 404

    project_info = {
        'project_id': project[0],
        'title': project[1],
        'abstract': project[2],
        'status': project[3],
        'start_date': project[4],
        'staff_id': project[5]
    }
    cursor.close()

    # Get all professors for project lead selection
    cursor = g.conn.execute(text("SELECT staff_id, name FROM Professor ORDER BY name"))
    professors = []
    for result in cursor:
        professors.append({
            'staff_id': result[0],
            'name': result[1]
        })
    cursor.close()

    # Get project's current required skills
    cursor = g.conn.execute(text("""
        SELECT skill_id
        FROM Requires_Skill
        WHERE project_id = :project_id
    """), {'project_id': project_id})

    current_skills = []
    for result in cursor:
        current_skills.append(result[0])
    cursor.close()

    # Get all skills
    skills = get_all_skills()

    return render_template("projects/edit.html",
                          project=project_info,
                          professors=professors,
                          skills=skills,
                          current_skills=current_skills)

#APPLYING TO PROJECTS
# Add this route to enable students to apply to projects
@app.route('/projects/<project_id>/apply', methods=['GET', 'POST'])
def apply_to_project(project_id):
    if request.method == 'POST':
        student_id = request.form['student_id']

        # Check if student has already applied
        cursor = g.conn.execute(text("""
            SELECT 1 FROM Applies_To_Project
            WHERE student_id = :student_id AND project_id = :project_id
        """), {
            "student_id": student_id,
            "project_id": project_id
        })

        existing_application = cursor.fetchone()
        cursor.close()

        if existing_application:
            return "You have already applied for this project", 400

        # Insert new application
        try:
            g.conn.execute(text("""
                INSERT INTO Applies_To_Project (student_id, project_id)
                VALUES (:student_id, :project_id)
            """), {
                "student_id": student_id,
                "project_id": project_id
            })

            return redirect(url_for('view_project', project_id=project_id))
        except Exception as e:
            return f"Error submitting application: {str(e)}", 500

    # GET request - show the application form
    # Get project details
    cursor = g.conn.execute(text("""
        SELECT p.project_id, p.title, p.abstract, p.status, p.start_date,
               pr.name as professor_name
        FROM Project p
        JOIN Leads_Project lp ON p.project_id = lp.project_id
        JOIN Professor pr ON lp.staff_id = pr.staff_id
        WHERE p.project_id = :project_id
    """), {"project_id": project_id})

    project = cursor.fetchone()
    cursor.close()

    if not project:
        return "Project not found", 404

    project_info = {
        'project_id': project[0],
        'title': project[1],
        'abstract': project[2],
        'status': project[3],
        'start_date': project[4],
        'professor_name': project[5]
    }

    # Get all students for dropdown
    cursor = g.conn.execute(text("""
        SELECT student_id, name FROM Student ORDER BY name
    """))

    students = []
    for result in cursor:
        students.append({
            'student_id': result[0],
            'name': result[1]
        })
    cursor.close()

    return render_template('projects/apply.html',
                          project=project_info,
                          students=students)


	#
	# Flask uses Jinja templates, which is an extension to HTML where you can
	# pass data to a template and dynamically generate HTML based on the data
	# (you can think of it as simple PHP)
	# documentation: https://realpython.com/primer-on-jinja-templating/
	#
	# You can see an example template in templates/index.html
	#
	# context are the variables that are passed to the template.
	# for example, "data" key in the context variable defined below will be
	# accessible as a variable in index.html:
	#
	#     # will print: [u'grace hopper', u'alan turing', u'ada lovelace']
	#     <div>{{data}}</div>
	#
	#     # creates a <div> tag for each element in data
	#     # will print:
	#     #
	#     #   <div>grace hopper</div>
	#     #   <div>alan turing</div>
	#     #   <div>ada lovelace</div>
	#     #
	#     {% for n in data %}
	#     <div>{{n}}</div>
	#     {% endfor %}
	#
    #context = dict(data = names)



#
# This is an example of a different path.  You can see it at:
#
#     localhost:8111/another
#
# Notice that the function name is another() rather than index()
# The functions for each app.route need to have different names
#



if __name__ == "__main__":
	import click

	@click.command()
	@click.option('--debug', is_flag=True)
	@click.option('--threaded', is_flag=True)
	@click.argument('HOST', default='0.0.0.0')
	@click.argument('PORT', default=8111, type=int)
	def run(debug, threaded, host, port):
		"""
		This function handles command line parameters.
		Run the server using:

			python server.py

		Show the help text using:

			python server.py --help

		"""

		HOST, PORT = host, port
		print("running on %s:%d" % (HOST, PORT))
		app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)
		
		run()

