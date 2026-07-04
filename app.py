from flask import Flask, render_template, request, redirect, session,flash
from db import get_connection
from routes.auth import auth 


app = Flask(__name__)

app.secret_key="hpgas123"

app.register_blueprint(auth)

@app.route("/dashboard")
def dashboard():

    if "admin" not in session:
        return redirect("/")

    conn = get_connection()
    cursor = conn.cursor()

    # Total Customers
    cursor.execute("SELECT COUNT(*) FROM customers")
    total_customers = cursor.fetchone()[0]

    # Total Connections
    cursor.execute("SELECT COUNT(*) FROM gas_connections")
    total_connections = cursor.fetchone()[0]

    # Pending Connections
    cursor.execute("""
        SELECT COUNT(*)
        FROM gas_connections
        WHERE status='Pending'
    """)
    pending_connections = cursor.fetchone()[0]

    # Active Bookings
    cursor.execute("""
        SELECT COUNT(*)
        FROM bookings
        WHERE delivery_status IN ('Pending','Out for Delivery')
    """)
    active_bookings = cursor.fetchone()[0]

    # Delivered Cylinders
    cursor.execute("""
        SELECT COUNT(*)
        FROM bookings
        WHERE delivery_status='Delivered'
    """)
    delivered_cylinders = cursor.fetchone()[0]

    # Total Employees
    cursor.execute("""
        SELECT COUNT(*)
        FROM employees
        WHERE status='Active'
    """)
    total_employees = cursor.fetchone()[0]

    # Today's Revenue
    cursor.execute("""
        SELECT IFNULL(SUM(amount),0)
        FROM payments
        WHERE payment_date = CURDATE()
    """)
    today_revenue = cursor.fetchone()[0]

    return render_template(
        "dashboard.html",

        total_customers=total_customers,
        total_connections=total_connections,
        pending_connections=pending_connections,
        active_bookings=active_bookings,
        delivered_cylinders=delivered_cylinders,
        total_employees=total_employees,
        today_revenue=today_revenue
    )


@app.route("/customer")
def customer():
    return render_template("customer.html")


@app.route("/save_customer", methods=["POST"])
def save_customer():
    fullname = request.form["full_name"]
    mobile = request.form["mobile"]
    email = request.form["email"]
    address = request.form["address"]

    conn=get_connection()
    cursor = conn.cursor()

    query = """
    INSERT INTO customers(full_name,mobile,email,address)
    VALUES(%s,%s,%s,%s)
    """

    cursor.execute(query,(fullname,mobile,email,address))
    conn.commit()
    flash("Customer Added Successfully!", "success")

    return redirect("/customers")


@app.route("/customers")
def customers():

    search = request.args.get("search", "")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if search:

        query = """
        SELECT *
        FROM customers
        WHERE full_name LIKE %s
        OR mobile LIKE %s
        ORDER BY id ASC
        """

        value = "%" + search + "%"

        cursor.execute(query, (value, value))

    else:

        cursor.execute("SELECT * FROM customers ORDER BY id ASC")

    customers = cursor.fetchall()

    return render_template(
        "customers.html",
        customer=customers,
        search=search
    )


@app.route("/edit_customer/<int:id>")
def edit_customer(id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = "SELECT * FROM customers WHERE id=%s"
    cursor.execute(query,(id,))

    customer = cursor.fetchone()

    return render_template("edit_customer.html",customer = customer)



@app.route("/update_customer",methods=["POST"])
def update_customer():
    id = request.form["id"]
    fullname = request.form["full_name"]
    mobile = request.form["mobile"]
    email = request.form["email"]
    address = request.form["address"]

    conn = get_connection()
    cursor = conn.cursor()

    query = """
    UPDATE customers
    SET full_name=%s,
    mobile=%s,
    email=%s,
    address=%s WHERE id = %s
    """

    cursor.execute(query,(fullname,mobile,email,address,id))
    conn.commit()
    flash("Customer Updated Successfully!", "info")

    return redirect("/customers")


@app.route("/delete_customer/<int:id>")
def delete_customer(id):

    conn = get_connection()
    cursor = conn.cursor()

    query = "DELETE FROM customers WHERE id=%s"

    cursor.execute(query,(id,))
    conn.commit()
    flash("Customer Deleted Successfully!", "danger")

    return redirect("/customers")




@app.route("/new_connection")
def new_connection():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT id, full_name
    FROM customers
    WHERE id NOT IN (
        SELECT customer_id
        FROM gas_connections
        WHERE status='Approved'
    )
    """

    cursor.execute(query)
    customers = cursor.fetchall()

    return render_template(
        "new_connection.html",
        customers=customers
    )

@app.route("/save_connection", methods=["POST"])
def save_connection():

    customer_id = request.form["customer_id"]
    
    connection_type = request.form["connection_type"]
    aadhaar_no = request.form["aadhaar_no"]
    deposit = request.form["deposit"]
    connection_date = request.form["issue_date"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT MAX(id) FROM gas_connections")

    last_id = cursor.fetchone()[0]

    if last_id is None:
        last_id = 0

    connection_no = f"HP{last_id + 1:04d}"

    query = """
    INSERT INTO gas_connections(
    customer_id,
    connection_no,
    connection_type,
    aadhaar_no,
    deposit,
    connection_date,
    status)

    VALUES(%s,%s,%s,%s,%s,%s,%s)
    """

    cursor.execute(
        query,
        (
            customer_id,
            connection_no,
            connection_type,
            aadhaar_no,
            deposit,
            connection_date,
            "Pending"
        )
    )

    conn.commit()

    return redirect("/connections")


@app.route("/connections")
def connections():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT gc.id,
           gc.connection_no,
           c.full_name,
           gc.connection_type,
           gc.aadhaar_no,
           gc.deposit,
           gc.connection_date,
           gc.status
    FROM gas_connections gc
    JOIN customers c
    ON gc.customer_id=c.id
    """

    cursor.execute(query)

    connections = cursor.fetchall()

    return render_template(
        "connections.html",
        connections=connections
    )



@app.route("/approve_connection/<int:id>")
def approve_connection(id):

    conn = get_connection()
    cursor = conn.cursor()

    query = """
    UPDATE gas_connections
    SET status='Approved'
    WHERE id=%s
    """

    cursor.execute(query, (id,))
    conn.commit()

    return redirect("/connections")



@app.route("/new_booking")
def new_booking():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT gc.id,
           gc.connection_no,
           c.full_name
    FROM gas_connections gc
    JOIN customers c
    ON gc.customer_id=c.id
    WHERE gc.status='Approved'
    """

    cursor.execute(query)

    connections = cursor.fetchall()

    return render_template(
        "new_booking.html",
        connections=connections
    )



@app.route("/save_booking",methods=["POST"])
def save_booking():

    connection_id = request.form["connection_id"]
    booking_date = request.form["booking_date"]
    cylinder_type = request.form["cylinder_type"]
    quantity = request.form["quantity"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT customer_id FROM gas_connections WHERE id=%s",
        (connection_id,)
    )

    row = cursor.fetchone()

    customer_id = row["customer_id"]

    query = """
    INSERT INTO bookings(
    customer_id,
    connection_id,
    booking_date,
    cylinder_type,
    quantity,
    delivery_status)

    VALUES(%s,%s,%s,%s,%s,%s)
    """

    cursor.execute(
        query,
        (
            customer_id,
            connection_id,
            booking_date,
            cylinder_type,
            quantity,
            "Pending"
        )
    )

    conn.commit()

    return redirect("/bookings")


@app.route("/delete_booking/<int:id>")
def delete_booking(id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM bookings WHERE id=%s",
        (id,)
    )

    conn.commit()

    return redirect("/bookings")



@app.route("/new_payment")
def new_payment():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT b.id,
           c.full_name,
           gc.connection_no
    FROM bookings b
    JOIN customers c
    ON b.customer_id=c.id
    JOIN gas_connections gc
    ON b.connection_id = gc.id
    WHERE b.delivery_status='pending'
    """

    cursor.execute(query)
    bookings =cursor.fetchall()

    return render_template("new_payment.html",bookings=bookings)



@app.route("/save_payment",methods=["POST"])
def save_payment():

    booking_id = request.form["booking_id"]
    amount = request.form["amount"]
    payment_method = request.form["payment_method"]
    payment_date = request.form["payment_date"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM payments")
    count = cursor.fetchone()[0]

    receipt_no = f"RCPT{count+1:04d}"

    query = """
    INSERT INTO payments(
            booking_id,
            amount,
            payment_method,
            payment_date,
            payment_status,
            receipt_no)
            
            VALUES(%s,%s,%s,%s,%s,%s)"""
    
    cursor.execute(query,(booking_id,
                        amount,
                        payment_method,
                        payment_date,
                        "paid",
                        receipt_no))
    
    conn.commit()

    return redirect("/payments")


@app.route("/payments")
def payments():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT p.id,
           c.full_name,
           p.amount,
           p.payment_method,
           p.payment_date,
           p.receipt_no,
           p.payment_status

    FROM payments p

    JOIN bookings b
    ON p.booking_id=b.id

    JOIN customers c
    ON b.customer_id=c.id
    """

    cursor.execute(query)

    payments = cursor.fetchall()

    return render_template("payments.html", payments=payments)



@app.route("/invoice/<int:id>")
def invoice(id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT
        p.receipt_no,
        p.amount,
        p.payment_method,
        p.payment_date,

        c.full_name,
        c.mobile,
        c.address,

        gc.connection_no,

        b.booking_date,
        b.cylinder_type,
        b.quantity

    FROM payments p

    JOIN bookings b
    ON p.booking_id=b.id

    JOIN customers c
    ON b.customer_id=c.id

    JOIN gas_connections gc
    ON b.connection_id=gc.id

    WHERE p.id=%s
    """

    cursor.execute(query, (id,))
    invoice = cursor.fetchone()

    return render_template("invoice.html", invoice=invoice)



@app.route("/new_employee")
def new_employee():
    return render_template("new_employee.html")


@app.route("/save_employee", methods=["POST"])
def save_employee():

    employee_name = request.form["employee_name"]
    mobile = request.form["mobile"]
    email = request.form["email"]
    designation = request.form["designation"]
    salary = request.form["salary"]
    joining_date = request.form["joining_date"]
    status = request.form["status"]

    conn = get_connection()
    cursor = conn.cursor()

    query = """
    INSERT INTO employees(
        employee_name,
        mobile,
        email,
        designation,
        salary,
        joining_date,
        status
    )
    VALUES(%s,%s,%s,%s,%s,%s,%s)
    """

    cursor.execute(query, (
        employee_name,
        mobile,
        email,
        designation,
        salary,
        joining_date,
        status
    ))

    conn.commit()

    return redirect("/employees")


@app.route("/employees")
def employees():

    search = request.args.get("search", "")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if search:

        query = """
        SELECT *
        FROM employees
        WHERE employee_name LIKE %s
           OR mobile LIKE %s
        ORDER BY id DESC
        """

        value = "%" + search + "%"

        cursor.execute(query, (value, value))

    else:

        cursor.execute("""
            SELECT *
            FROM employees
            ORDER BY id DESC
        """)

    employees = cursor.fetchall()

    return render_template(
        "employees.html",
        employees=employees,
        search=search
    )

@app.route("/edit_employee/<int:id>")
def edit_employee(id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM employees WHERE id=%s",
        (id,)
    )

    employee = cursor.fetchone()

    return render_template(
        "edit_employee.html",
        employee=employee
    )



@app.route("/update_employee", methods=["POST"])
def update_employee():

    id = request.form["id"]
    employee_name = request.form["employee_name"]
    mobile = request.form["mobile"]
    email = request.form["email"]
    designation = request.form["designation"]
    salary = request.form["salary"]
    joining_date = request.form["joining_date"]
    status = request.form["status"]

    conn = get_connection()
    cursor = conn.cursor()

    query = """
    UPDATE employees
    SET employee_name=%s,
        mobile=%s,
        email=%s,
        designation=%s,
        salary=%s,
        joining_date=%s,
        status=%s
    WHERE id=%s
    """

    cursor.execute(query, (
        employee_name,
        mobile,
        email,
        designation,
        salary,
        joining_date,
        status,
        id
    ))

    conn.commit()

    return redirect("/employees")


@app.route("/delete_employee/<int:id>")
def delete_employee(id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM employees WHERE id=%s",
        (id,)
    )

    conn.commit()

    return redirect("/employees")



@app.route("/edit_connection/<int:id>")
def edit_connection(id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM gas_connections WHERE id=%s",
        (id,)
    )

    connection = cursor.fetchone()

    cursor.execute("""
        SELECT id, full_name
        FROM customers
        ORDER BY full_name
    """)

    customers = cursor.fetchall()

    return render_template(
        "edit_connection.html",
        connection=connection,
        customers=customers
    )

@app.route("/update_connection/<int:id>", methods=["POST"])
def update_connection(id):

    customer_id = request.form["customer_id"]
    connection_type = request.form["connection_type"]
    aadhaar_no = request.form["aadhaar_no"]
    deposit = request.form["deposit"]
    connection_date = request.form["connection_date"]
    status = request.form["status"]

    conn = get_connection()
    cursor = conn.cursor()

    query = """
    UPDATE gas_connections
    SET
        customer_id=%s,
        connection_type=%s,
        aadhaar_no=%s,
        deposit=%s,
        connection_date=%s,
        status=%s
    WHERE id=%s
    """

    cursor.execute(
        query,
        (
            customer_id,
            connection_type,
            aadhaar_no,
            deposit,
            connection_date,
            status,
            id
        )
    )

    conn.commit()

    return redirect("/connections")


@app.route("/delete_connection/<int:id>")
def delete_connection(id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM gas_connections WHERE id=%s",
        (id,)
    )

    conn.commit()

    return redirect("/connections")


@app.route("/bookings")
def bookings():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT
        b.id,
        c.full_name,
        gc.connection_no,
        b.booking_date,
        b.cylinder_type,
        b.quantity,
        b.delivery_status

    FROM bookings b

    JOIN customers c
    ON b.customer_id=c.id

    JOIN gas_connections gc
    ON b.connection_id=gc.id
    """

    cursor.execute(query)

    bookings = cursor.fetchall()

    return render_template("bookings.html", bookings=bookings)



@app.route("/edit_booking/<int:id>")
def edit_booking(id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM bookings WHERE id=%s",
        (id,)
    )

    booking = cursor.fetchone()

    return render_template(
        "edit_booking.html",
        booking=booking
    )



@app.route("/cancel_booking/<int:id>")
def cancel_booking(id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE bookings
        SET delivery_status='Cancelled'
        WHERE id=%s
    """, (id,))

    conn.commit()

    return redirect("/bookings")


@app.route("/new_delivery")
def new_delivery():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Delivered नसलेल्या Bookings
    cursor.execute("""
        SELECT b.id,
               c.full_name,
               gc.connection_no
        FROM bookings b
        JOIN customers c
        ON b.customer_id=c.id
        JOIN gas_connections gc
        ON b.connection_id=gc.id
        WHERE b.delivery_status!='Delivered'
    """)

    bookings = cursor.fetchall()

    # Active Delivery Boys
    cursor.execute("""
        SELECT *
        FROM employees
        WHERE designation='Delivery Boy'
        AND status='Active'
    """)

    employees = cursor.fetchall()

    return render_template(
        "new_delivery.html",
        bookings=bookings,
        employees=employees
    )


@app.route("/save_delivery", methods=["POST"])
def save_delivery():

    booking_id = request.form["booking_id"]
    employee_id = request.form["employee_id"]
    delivery_date = request.form["delivery_date"]
    delivery_status = request.form["status"]
    #remarks = request.form["remarks"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO deliveries(
        booking_id,
        employee_id,
        delivery_date,
        delivery_status
        #remarks
                   )

        VALUES(%s,%s,%s,%s)
    """,(
        booking_id,
        employee_id,
        delivery_date,
        delivery_status
        #remarks
    ))

    # Booking Status पण Update करा
    cursor.execute("""
        UPDATE bookings
        SET delivery_status=%s
        WHERE id=%s
    """,(delivery_status, booking_id))

    conn.commit()

    return redirect("/deliveries")



@app.route("/deliveries")
def deliveries():

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""

SELECT
d.id,
c.full_name,
gc.connection_no,
e.employee_name,
d.delivery_date,
d.delivery_status
#d.remarks

FROM deliveries d

JOIN bookings b
ON d.booking_id=b.id

JOIN customers c
ON b.customer_id=c.id

JOIN gas_connections gc
ON b.connection_id=gc.id

JOIN employees e
ON d.employee_id=e.id

""")

    deliveries = cursor.fetchall()

    return render_template(
        "deliveries.html",
        deliveries=deliveries
    )



@app.route("/edit_delivery/<int:id>")
def edit_delivery(id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Current Delivery
    cursor.execute(
        "SELECT * FROM deliveries WHERE id=%s",
        (id,)
    )
    delivery = cursor.fetchone()

    # Booking List
    cursor.execute("""
        SELECT b.id,
               c.full_name,
               gc.connection_no
        FROM bookings b
        JOIN customers c
        ON b.customer_id=c.id
        JOIN gas_connections gc
        ON b.connection_id=gc.id
    """)
    bookings = cursor.fetchall()

    # Delivery Boys
    cursor.execute("""
        SELECT *
        FROM employees
        WHERE designation='Delivery Boy'
    """)
    employees = cursor.fetchall()

    return render_template(
        "edit_delivery.html",
        delivery=delivery,
        bookings=bookings,
        employees=employees
    )



@app.route("/update_delivery", methods=["POST"])
def update_delivery():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE deliveries

    SET booking_id=%s,
        employee_id=%s,
        delivery_date=%s,
        delivery_status=%s


    WHERE id=%s
    """,(

        request.form["booking_id"],
        request.form["employee_id"],
        request.form["delivery_date"],
        request.form["delivery_status"],
       # request.form["remarks"],
        request.form["id"]

    ))

    # Booking Status सुद्धा Update करा
    cursor.execute("""
        UPDATE bookings
        SET delivery_status=%s
        WHERE id=%s
    """, (
        request.form["delivery_status"],
        request.form["booking_id"]
    ))

    conn.commit()

    return redirect("/deliveries")



@app.route("/delete_delivery/<int:id>")
def delete_delivery(id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM deliveries WHERE id=%s",
        (id,)
    )

    conn.commit()

    return redirect("/deliveries")


@app.route("/update_booking", methods=["POST"])
def update_booking():

    conn = get_connection()
    cursor = conn.cursor()

    query = """
    UPDATE bookings
    SET booking_date=%s,
        cylinder_type=%s,
        quantity=%s,
        delivery_status=%s
    WHERE id=%s
    """

    cursor.execute(query, (
        request.form["booking_date"],
        request.form["cylinder_type"],
        request.form["quantity"],
        request.form["delivery_status"],
        request.form["id"]
    ))

    conn.commit()

    return redirect("/bookings")

@app.route("/edit_payment/<int:id>")
def edit_payment(id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM payments WHERE id=%s",
        (id,)
    )

    payment = cursor.fetchone()

    return render_template(
        "edit_payment.html",
        payment=payment
    )

@app.route("/update_payment/<int:id>", methods=["POST"])
def update_payment(id):

    amount = request.form["amount"]
    payment_method = request.form["payment_method"]
    payment_date = request.form["payment_date"]
    #status = request.form["status"]

    conn = get_connection()
    cursor = conn.cursor()

    query = """
    UPDATE payments
    SET
        amount=%s,
        payment_method=%s,
        payment_date=%s        
    WHERE id=%s
    """

    cursor.execute(
        query,
        (
            amount,
            payment_method,
            payment_date,
            id
        )
    )

    conn.commit()

    return redirect("/payments")


if __name__ == '__main__':
    app.run(debug=True)