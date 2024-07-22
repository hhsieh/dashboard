import os
from flask import Flask, render_template_string, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from sqlalchemy.ext.hybrid import hybrid_property
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape
import folium

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}@granby.kbs.msu.edu/metadata"
db = SQLAlchemy(app)

# Define the Site model with geometry column
class Site(db.Model):
    __tablename__ = 'site'
    __table_args__ = {'schema': 'test'}

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    geometry = db.Column(Geometry('POINT', srid=4326))  # Assuming POINT geometry with SRID 4326

    @hybrid_property
    def latitude(self):
        if self.geometry:
            point = to_shape(self.geometry)
            return point.y  # Latitude
        return None

    @hybrid_property
    def longitude(self):
        if self.geometry:
            point = to_shape(self.geometry)
            return point.x  # Longitude
        return None

    def __repr__(self):
        return f"<Site(id={self.id}, name={self.name}, geometry={self.geometry})>"

# Define the Fertilization model
class Fertilization(db.Model):
    __tablename__ = 'n2o_project_fertilization'
    __table_args__ = {'schema': 'test'}

    site = db.Column(db.String, primary_key = True)
    dataset_name = db.Column(db.String, primary_key = True)
    fertilization_date = db.Column(db.Date, primary_key = True)
    treatment = db.Column(db.String, primary_key = True)
    replicate = db.Column(db.String, primary_key = True)
    nitrogen_rate = db.Column(db.Numeric)
    formulation = db.Column(db.String)
    unit = db.Column(db.String)
    placement = db.Column(db.String)

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

@app.route('/data', methods=['GET'])
def get_data():
    try:
        sites = Site.query.all()
        if sites:
            return jsonify([{
                'id': site.id,
                'name': site.name,
                'longitude': site.longitude,
                'latitude': site.latitude
            } for site in sites])
        else:
            return jsonify({"message": "No data found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/map', methods=['GET'])
def map_view():
    sites = Site.query.all()
    map_center = [0, 0]  # Default map center
    site_coords = []

    if sites:
        # Get the coordinates of the first site to center the map
        first_site = sites[0]
        map_center = [first_site.latitude, first_site.longitude]

        # Collect site coordinates
        for site in sites:
            if site.latitude and site.longitude:
                site_coords.append((site.latitude, site.longitude, site.name))

    # Create a Folium map
    m = folium.Map(location=map_center, zoom_start=2)

    # Add markers to the map
    for lat, lon, name in site_coords:
        folium.Marker(
            location=[lat, lon],
            popup=name,
            icon=folium.Icon(icon="info-sign")
        ).add_to(m)

    # Generate the map HTML
    map_html = m._repr_html_()

    # Render the map in a simple HTML template
    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Site Map</title>
        </head>
        <body>
            <h1>Site Map</h1>
            {{ map_html|safe }}
        </body>
        </html>
    """, map_html=map_html)

@app.route('/fertilization_data', methods=['GET'])
def fertilization_data():
    selected_site = request.args.get('site')
    selected_dataset = request.args.get('dataset')

    # Query to get all distinct sites
    sites = db.session.query(Site.name).distinct().all()

    # Query to get all distinct datasets for the selected site
    datasets = []
    if selected_site:
        datasets = db.session.query(Fertilization.dataset_name).filter_by(site=selected_site).distinct().all()

    # Query to get fertilization records based on selected site and dataset
    records = []
    if selected_site and selected_dataset:
        records = db.session.query(Fertilization).filter_by(site=selected_site, dataset_name=selected_dataset).all()

    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Fertilization Data</title>
        </head>
        <body>
            <h1>Select Fertilization Data</h1>
            <form method="GET">
                <label for="site">Select Site:</label>
                <select id="site" name="site" onchange="this.form.submit()">
                    <option value="">Select a site</option>
                    {% for site in sites %}
                    <option value="{{ site[0] }}" {% if site[0] == selected_site %}selected{% endif %}>{{ site[0] }}</option>
                    {% endfor %}
                </select>
                
                <label for="dataset">Select Dataset:</label>
                <select id="dataset" name="dataset" onchange="this.form.submit()">
                    <option value="">Select a dataset</option>
                    {% for dataset in datasets %}
                    <option value="{{ dataset[0] }}" {% if dataset[0] == selected_dataset %}selected{% endif %}>{{ dataset[0] }}</option>
                    {% endfor %}
                </select>
            </form>
            
            {% if records %}
            <h2>Fertilization Records</h2>
            <table border="1">
                <thead>
                    <tr>
                        <th>Site</th>
                        <th>Dataset Name</th>
                        <th>Fertilization Date</th>
                        <th>Treatment</th>
                        <th>Replicate</th>
                        <th>Nitrogen Rate</th>
                        <th>Formulation</th>
                        <th>Unit</th>
                        <th>Placement</th>
                    </tr>
                </thead>
                <tbody>
                    {% for record in records %}
                    <tr>
                        <td>{{ record.site }}</td>
                        <td>{{ record.dataset_name }}</td>
                        <td>{{ record.fertilization_date }}</td>
                        <td>{{ record.treatment }}</td>
                        <td>{{ record.replicate }}</td>
                        <td>{{ record.nitrogen_rate }}</td>
                        <td>{{ record.formulation }}</td>
                        <td>{{ record.unit }}</td>
                        <td>{{ record.placement }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% endif %}
        </body>
        </html>
    """, sites=sites, datasets=datasets, selected_site=selected_site, selected_dataset=selected_dataset, records=records)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

