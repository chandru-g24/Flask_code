from flask import Flask, render_template, request, redirect, url_for, jsonify
from neo4j import GraphDatabase, basic_auth

app = Flask(__name__)

# Neo4j connection
uri = "neo4j+s://c19e57c4.databases.neo4j.io"
username = "neo4j"
password = "a1wAD9LdcVk5gwMXV9Kt5Gb0o8J76KocBMOeVFOMUds"
driver = GraphDatabase.driver(uri, auth=basic_auth(username, password))


@app.route('/')
def index():
    with driver.session() as session:
        leads_result = session.run("""
            MATCH (l:Lead)-[:CUSTOMER_OF_LEAD]->(c:Customer)
            RETURN l, c
        """)
        leads = []
        for record in leads_result:
            lead = record["l"]
            customer = record["c"]
            leads.append({
                "name": lead["name"],
                "customer_name": customer["name"],
                "customer_phone": customer["phone_number"],
                "model": lead["model"],
                "variant": lead["variant"],
                "salesman": lead["salesman"]
            })
    return render_template('index.html', leads=leads)

@app.route('/add_lead', methods=['GET', 'POST'])
def add_lead():
    if request.method == 'POST':
        customer_name = request.form['customer_name']
        customer_phone = request.form['customer_phone']
        customer_location = request.form['customer_location']
        lead_type = request.form['lead_type']
        model = request.form['model']
        variant = request.form['variant']
        touch_point = request.form['touch_point']
        business_source = request.form['business_source']
        lead_quality = request.form['lead_quality']
        salesman = request.form['salesman']

        with driver.session() as session:
            session.run("""
                MERGE (c:Customer {name: $customer_name, phone_number: $customer_phone, location: $customer_location})
                CREATE (l:Lead {
                    name: $customer_name, 
                    phone_number: $customer_phone, 
                    leadtype: $lead_type, 
                    level: $lead_quality, 
                    touchpoint: $touch_point, 
                    source: $business_source,
                    model: $model,
                    variant: $variant,
                    location: $customer_location,
                    salesman: $salesman
                })
                MERGE (l)-[:CUSTOMER_OF_LEAD]->(c)
                WITH l
                MATCH (v:Variant{name: $variant})<-[:HAS_VARIANT]-(m:Model{name: $model})
                MERGE (l)-[:PREFERENCE]->(m)
                WITH l
                MATCH (s:Salesman{name: $salesman})
                MERGE (l)-[:ASSIGNED_TO]->(s)
            """, {
                "customer_name": customer_name,
                "customer_phone": customer_phone,
                "customer_location": customer_location,
                "lead_type": lead_type,
                "lead_quality": lead_quality,
                "touch_point": touch_point,
                "business_source": business_source,
                "model": model,
                "variant": variant,
                "salesman": salesman
            })
        return redirect(url_for('index'))

    with driver.session() as session:
        model_query = session.run("MATCH (m:Model) RETURN m.name AS name")
        models = [record["name"] for record in model_query]
    return render_template('add_lead.html', models=models)

@app.route('/edit_lead/<name>/<phone>', methods=['GET', 'POST'])
def edit_lead(name, phone):
    with driver.session() as session:
        lead_result = session.run("""
            MATCH (l:Lead {name: $name, phone_number: $phone})-[:CUSTOMER_OF_LEAD]->(c:Customer)
            RETURN l, c
        """, {"name": name, "phone": phone})
        lead_record = lead_result.single()
        lead = lead_record["l"]
        customer = lead_record["c"]

        if request.method == 'POST':
            customer_name = request.form['customer_name']
            customer_phone = request.form['customer_phone']
            customer_location = request.form['customer_location']
            lead_type = request.form['lead_type']
            model = request.form['model']
            variant = request.form['variant']
            touch_point = request.form['touch_point']
            business_source = request.form['business_source']
            lead_quality = request.form['lead_quality']
            salesman = request.form['salesman']

            session.run("""
                MATCH (l:Lead {name: $name, phone_number: $phone})-[:CUSTOMER_OF_LEAD]->(c:Customer)
                SET l.name = $customer_name,
                    l.phone_number = $customer_phone,
                    l.leadtype = $lead_type,
                    l.level = $lead_quality,
                    l.touchpoint = $touch_point,
                    l.source = $business_source,
                    l.model = $model,
                    l.variant = $variant,
                    l.location = $customer_location,
                    l.salesman = $salesman,
                    c.name = $customer_name,
                    c.phone_number = $customer_phone,
                    c.location = $customer_location
            """, {
                "name": name,
                "phone": phone,
                "customer_name": customer_name,
                "customer_phone": customer_phone,
                "customer_location": customer_location,
                "lead_type": lead_type,
                "lead_quality": lead_quality,
                "touch_point": touch_point,
                "business_source": business_source,
                "model": model,
                "variant": variant,
                "salesman": salesman
            })
            return redirect(url_for('index'))

        model_query = session.run("MATCH (m:Model) RETURN m.name AS name")
        models = [record["name"] for record in model_query]

        variant_query = session.run("""
            MATCH (m:Model {name: $model})-[:HAS_VARIANT]->(v:Variant)
            RETURN v.name AS name
        """, {"model": lead["model"]})
        variants = [record["name"] for record in variant_query]

        salesman_query = session.run("""
            MATCH (m:Model {name: $model})<-[:PREFERENCE]-(l:Lead)-[:ASSIGNED_TO]->(s:Salesman)
            WHERE l.location = $location
            RETURN DISTINCT s.name AS name
        """, {"model": lead["model"], "location": lead["location"]})
        salesmen = [record["name"] for record in salesman_query]

    return render_template('edit_lead.html', lead=lead, customer=customer, models=models, variants=variants, salesmen=salesmen)

@app.route('/delete_lead/<name>/<phone>', methods=['GET'])
def delete_lead(name, phone):
    with driver.session() as session:
        session.run("MATCH (l:Lead {name: $name, phone_number: $phone}),(c:Customer{name: $name, phone_number: $phone}) DETACH DELETE l,c", {"name": name, "phone": phone})
    return redirect(url_for('index'))

@app.route('/get_variants', methods=['GET'])
def get_variants():
    model = request.args.get('model')

    query = """
    MATCH (m:Model)-[:HAS_VARIANT]-(v:Variant)
    WHERE m.name = $model
    RETURN v.name AS variant
    """

    with driver.session() as session:
        results = session.run(query, model=model)
        variants = [record['variant'] for record in results]

    return jsonify({"variants": variants})

@app.route('/get_salesmen', methods=['GET'])
def get_salesmen():
    model = request.args.get('model')
    location = request.args.get('location')
    quality = request.args.get('quality')

    query = f"""
    MATCH (l:Lead)-[:PREFERENCE]->(m:Model)<-[:HANDELS]-(s:Salesman)-[:WORKS_AT]->(sr:Showroom)
    WHERE m.name=$model AND toLower(sr.location) CONTAINS toLower($location)
    AND (
        ($quality = "High" AND s.experience = 3) OR
        ($quality = "Medium" AND s.experience = 2) OR
        ($quality = "Low" AND s.experience = 1)
    )
    RETURN DISTINCT(s.name) AS Salesman
    """

    with driver.session() as session:
        results = session.run(query, model=model, location=location, quality=quality)
        salesmen = [record["Salesman"] for record in results]

    return jsonify({"salesmen": salesmen})

if __name__ == '__main__':
    app.run(debug=True)
