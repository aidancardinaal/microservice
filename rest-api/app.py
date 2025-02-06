from flask import Flask, request, jsonify
import psycopg2
import os
import json

app = Flask(__name__)

# Database instellingen, tweede waarde van tuple is defaultvalue
DB_HOST = os.getenv('DB_HOST', 'postgres-db-service.default.svc.cluster.local')
DB_NAME = os.getenv('DB_NAME', 'postgresdb')
DB_USER = os.getenv('DB_USER', 'group8')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'psltest')

# Verbind met de PostgreSQL database
try:
    dbconnection = psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
except psycopg2.OperationalError as e:
    print(f"Error connecting to the database: {e}")
    exit()


@app.route("/experiments", methods=["POST"])
def create_experiment():
    data = request.get_json()

    # Valideer de invoer
    if not data or "experiment" not in data or "researcher" not in data or "sensors" not in data or "temperature_range" not in data:
        return jsonify({"error": "Missing required fields"}), 400

    experiment_id = data["experiment"]
    researcher = data["researcher"]
    sensors = data["sensors"]
    upper_threshold = data["temperature_range"]["upper_threshold"]
    lower_threshold = data["temperature_range"]["lower_threshold"]

    try:
        cursor = dbconnection.cursor()

        # SQL-query om het experiment op te slaan
        insert_query = """
            INSERT INTO experiments (experiment_id, researcher, sensors, upper_threshold, lower_threshold)
            VALUES (%s, %s, %s, %s, %s);
        """
        cursor.execute(insert_query, (experiment_id, researcher, sensors, upper_threshold, lower_threshold))

        # Bevestig de transactie
        dbconnection.commit()

        # Sluit de cursor en verbinding
        cursor.close()

    except psycopg2.Error as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"message": "Experiment created", "experiment_id": experiment_id}), 201


@app.route("/experiments/<experiment>/measurements", methods=["POST"])
def create_measurement(experiment):
    data = request.get_json()

    # Valideer of alle benodigdheden met het verzoek zijn meegestuurd
    if not data or "measurement_id" not in data or "timestamp" not in data or "temperature" not in data:
        return jsonify({"error": "Missing required fields"}), 400

    # Sla de values van de json payload op in variabelen
    measurement_id = data["measurement_id"]
    temperature = data["temperature"]
    timestamp = data["timestamp"]

    try:
        cursor = dbconnection.cursor()

        # SQL-query om de meting op te slaan
        insert_query = """
            INSERT INTO measurements (measurement_id, experiment_id, temperature, timestamp)
            VALUES (%s, %s, %s, %s);
        """
        cursor.execute(insert_query, (measurement_id, experiment, temperature, timestamp))

        # Bevestig de transactie
        dbconnection.commit()

        # Sluit de cursor en verbinding
        cursor.close()

    except psycopg2.Error as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"message": "Measurement saved successfully", "measurement_id": measurement_id}), 201


# Test functie
# @todo remove
@app.route("/check", methods=["GET"])
def check_if_experiment_exists():
    experiment_id = request.args.get('experiment-id')

    cursor = dbconnection.cursor()

    cursor.execute("""
        SELECT lower_threshold, upper_threshold
        FROM experiments 
        WHERE experiment_id = %s
    """, (experiment_id,))

    # Haal de eerste rij (experiment) dat matcht op uit de db
    experiment = cursor.fetchone()

    cursor.close()

    if experiment is None:
        return jsonify({"error": "Experiment not found"}), 404

    return jsonify({
        "lower_threshold": experiment[0],
        "upper_threshold": experiment[1]
    })


@app.route("/temperature/out-of-range", methods=["GET"])
def get_out_of_range_temperatures():
    experiment_id = request.args.get('experiment-id')

    if not experiment_id:
        return jsonify({"error": "Missing experiment-id parameter"}), 400

    cursor = dbconnection.cursor()

    # Haal de temperatuurgrenzen op uit de experimentconfiguratie
    cursor.execute("""
        SELECT lower_threshold, upper_threshold
        FROM experiments 
        WHERE experiment_id = %s
    """, (experiment_id,))

    # Haal de eerste rij (experiment) dat match op uit de db
    experiment = cursor.fetchone()

    if experiment is None:
        cursor.close()

        return jsonify({"error": "Experiment not found"}), 404

    lower_threshold, upper_threshold = experiment

    # Haal de metingen op die buiten het temperatuur bereik vallen
    cursor.execute("""
        SELECT timestamp, temperature 
        FROM measurements 
        WHERE experiment_id = %s AND (temperature < %s OR temperature > %s)
    """, (experiment_id, lower_threshold, upper_threshold))

    out_of_range_measurements = cursor.fetchall()

    # Format de resultaten zodat het lijst met dictoionaries wordt en goed als json gereturnd kan
    # worden
    result = [
        {"timestamp": row[0], "temperature": row[1]}
        for row in out_of_range_measurements
    ]

    cursor.close()

    return jsonify(result), 200


# Given an experiment, a start-time and an end-time, this endpoint should return
# the temperature measurements for the specified time-interval.

@app.route("/temperature", methods=["GET"])
def temperature_interval():
    experiment_id = request.args.get('experiment-id')
    start_time = request.args.get('start-time')
    end_time = request.args.get('end-time')

    if not experiment_id or not start_time or not end_time:
        return jsonify({"error": "Missing required parameters"}), 400

    cursor = dbconnection.cursor()

    # Query de temperaturen en tijdstamps die binnen gegeven interval en experiment vallen
    cursor.execute("""
        SELECT timestamp, temperature
        FROM measurements
        WHERE timestamp > %s AND timestamp < %s AND experiment_id = %s;
    """, (start_time, end_time, experiment_id))

    interval_measurements = cursor.fetchall()

    # Format de resultaten zodat het lijst met dictoionaries wordt en goed als json gereturnd kan
    # worden
    result = [
        {"timestamp": meting[0], "temperature": meting[1]}
        for meting in interval_measurements
    ]

    cursor.close()

    return jsonify(result), 200
