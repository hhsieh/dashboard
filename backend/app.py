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

class Treatment(db.Model):
    __tablename__ = 'n2o_project_treatments'
    __table_args__ = {'schema': 'test'}

    site = db.Column(db.String, primary_key = True)
    dataset = db.Column(db.String, primary_key = True)
    year = db.Column(db.String, primary_key = True)
    crop = db.Column(db.String)
    fertilization = db.Column(db.String)
    tillage = db.Column(db.String)
    nitrogen_inhibitor = db.Column(db.String)
    irrigation = db.Column(db.String)
    residue_treatment = db.Column(db.String)
    cover_crop = db.Column(db.String)
    liming = db.Column(db.String)
    relative_elevation_m = db.Column(db.String)

class Tillage(db.Model):
    __tablename__ = 'n2o_project_tillage'
    __table_args__ = {'schema': 'test'}

    site = db.Column(db.String, primary_key = True)
    dataset = db.Column(db.String, primary_key = True)
    tillage_date = db.Column(db.Date)
    treatment = db.Column(db.String)
    tillage_type = db.Column(db.String)
    tillage_depth_cm = db.Column(db.String)
    tillage_time = db.Column(db.String)
    comment = db.Column(db.String)


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
    m = folium.Map(location=map_center, zoom_start=3)

    # Add the ArcGIS climate zone tile layer
    folium.TileLayer(
        tiles='https://tiles.arcgis.com/tiles/TkMzk1ALQloG1Rga/arcgis/rest/services/World_Climate_Zones/MapServer/tile/{z}/{y}/{x}',
        attr='ESRI Climate Zone',
        name='ESRI Climate Zone'
    ).add_to(m)

    # Add markers to the map
    for lat, lon, name in site_coords:
        folium.Marker(
            location=[lat, lon],
            popup=name,
            icon=folium.Icon(icon="info-sign", color = 'black')
        ).add_to(m)

    # Add layer control
    folium.LayerControl().add_to(m)

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
                        <td>{{ record.dataset }}</td>
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


@app.route('/treatment', methods=['GET'])
def treatment_data():
    selected_site = request.args.get('site')
    selected_dataset = request.args.get('dataset')

    # Query to get all distinct sites
    sites = db.session.query(Site.name).distinct().all()

    # Query to get all distinct datasets for the selected site
    datasets = []
    if selected_site:
        datasets = db.session.query(Treatment.dataset).filter_by(site=selected_site).distinct().all()

    # Query to get fertilization records based on selected site and dataset
    records = []
    if selected_site and selected_dataset:
        records = db.session.query(Treatment).filter_by(site=selected_site, dataset=selected_dataset).all()

    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Treatment Data</title>
        </head>
        <body>
            <h1>Select Treatment Data</h1>
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
            <h2>Treatments</h2>
            <table border="1">
                <thead>
                    <tr>
                        <th>Site</th>
                        <th>Dataset</th>
                        <th>Year</th>
                        <th>Crop</th>
                        <th>Fertilization</th>
                        <th>Tillage</th>
                        <th>Nitrogen inhibitor</th>
                        <th>Irrigation</th>
                        <th>Residue treatment</th>
                        <th>Cover crop</th>
                        <th>Liming</th>
                        <th>Relative elevation (m)</th>
                    </tr>
                </thead>
                <tbody>
                    {% for record in records %}
                    <tr>
                        <td>{{ record.site }}</td>
                        <td>{{ record.dataset }}</td>
                        <td>{{ record.year }}</td>
                        <td>{{ record.crop }}</td>
                        <td>{{ record.fertilization }}</td>
                        <td>{{ record.tillage }}</td>
                        <td>{{ record.nitrogen_inhibitor }}</td>
                        <td>{{ record.irrigation }}</td>
                        <td>{{ record.residue_treatment }}</td>
                        <td>{{ record.cover_crop }}</td>
                        <td>{{ record.liming}}</td>
                        <td>{{ record.relative_elevation_m}}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% endif %}
        </body>
        </html>
    """, sites=sites, datasets=datasets, selected_site=selected_site, selected_dataset=selected_dataset, records=records)

@app.route('/tillage', methods=['GET'])
def tillage_data():
    selected_site = request.args.get('site')
    selected_dataset = request.args.get('dataset')

    # Query to get all distinct sites
    sites = db.session.query(Site.name).distinct().all()

    # Query to get all distinct datasets for the selected site
    datasets = []
    if selected_site:
        datasets = db.session.query(Tillage.dataset).filter_by(site=selected_site).distinct().all()

    # Query to get fertilization records based on selected site and dataset
    records = []
    if selected_site and selected_dataset:
        records = db.session.query(Tillage).filter_by(site=selected_site, dataset=selected_dataset).all()

    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Treatment Data</title>
        </head>
        <body>
            <h1>Select Treatment Data</h1>
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
            <h2>Treatments</h2>
            <table border="1">
                <thead>
                    <tr>
                        <th>Site</th>
                        <th>Dataset</th>
                        <th>Tillage date</th>
                        <th>Treatment</th>
                        <th>Tillage type</th>
                        <th>Tillage depth (cm)</th>
                        <th>Tillage time</th>
                        <th>Comment</th>
                    </tr>
                </thead>
                <tbody>
                    {% for record in records %}
                    <tr>
                        <td>{{ record.site }}</td>
                        <td>{{ record.dataset }}</td>
                        <td>{{ record.tillage_date }}</td>
                        <td>{{ record.treatment }}</td>
                        <td>{{ record.tillage_type }}</td>
                        <td>{{ record.tillage_depth_cm }}</td>
                        <td>{{ record.tillage_time }}</td>
                        <td>{{ record.comment }}</td>
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

