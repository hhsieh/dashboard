import os
from flask import Flask, render_template_string, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from sqlalchemy.ext.hybrid import hybrid_property
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape
import folium
import pandas as pd  # Add this line
import plotly.express as px
import plotly.io as pio
from sqlalchemy import Table, MetaData
from sqlalchemy import text  # Make sure to import text

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}@granby.kbs.msu.edu/metadata"

# Secondary database configuration
#app.config['SQLALCHEMY_BINDS'] = {
#    'secondary': f"postgresql://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}@granby.kbs.msu.edu/gas"
#}

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

class Fluxes(db.Model):
    __tablename__ = 'n2o_projects_fluxes'
    __table_args__ = {'schema': 'test'}

    site = db.Column(db.String, primary_key = True)
    dataset = db.Column(db.String, primary_key = True)
    sample_date = db.Column(db.Date, primary_key = True)
    #longitude = db.Column(db.Numeric)
    #latitude = db.Column(db.Numeric)
    treatment_name = db.Column(db.String, primary_key = True)
    replicate_name = db.Column(db.String, primary_key = True)
    crop = db.Column(db.String, primary_key = True)
    fertilization = db.Column(db.Boolean)
    tillage = db.Column(db.String)
    nitrogen_inhibitor = db.Column(db.String)
    irrigation = db.Column(db.String)
    gas = db.Column(db.String)
    flux = db.Column(db.Numeric)

                     
#class KBS_fluxes(db.Model):
#    __tablename__ = 'flux_results'
#    __table_args = {'schema': public}

#    study = db.Column(db.String, primary_key = True)
       

# Create database tables if they don't exist
with app.app_context():
    db.create_all()


#test database connections
@app.route('/test_db', methods = ['GET'])
def test_db():
    try:
        # Create engines explicitly
        primary_engine = db.get_engine(app)
        secondary_engine = db.get_engine(app, bind='secondary')

        # Test primary engine
        result_primary = primary_engine.execute('SELECT * FROM test.datasets LIMIT 1').fetchone()

        # Test secondary engine
        result_secondary = secondary_engine.execute('SELECT 1').fetchone()

        return f"Connected to databases successfully: Primary {result_primary[0]}, Secondary {result_secondary[0]}"
    except Exception as e:
        return f"Error connecting to databases: {str(e)}"
    
#@app.route('KBS_fluxes', methods = 'GET')
#def get_kbs_fluxes():


@app.route('/')
def front_page():
    routes = [
        {'name': 'Test DB Connection', 'url': '/test_db'},
        {'name': 'Data', 'url': '/data'},
        {'name': 'Map', 'url': '/map'},
        {'name': 'Fertilization Data', 'url': '/fertilization_data'},
        {'name': 'Treatment Data', 'url': '/treatment'},
        {'name': 'Tillage Data', 'url': '/tillage'},
        {'name': 'Fluxes Data', 'url': '/fluxes'}
    ]
    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Front Page</title>
        </head>
        <body>
            <h1>Welcome to the Ecological Data Application</h1>
            <ul>
                {% for route in routes %}
                    <li><a href="{{ route.url }}">{{ route.name }}</a></li>
                {% endfor %}
            </ul>
        </body>
        </html>
    """, routes=routes)

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



@app.route('/fluxes', methods=['GET'])
def fetch_fluxes_data():
    # Define the SQL query to fetch all rows from the view
    query = text("SELECT site, dataset, sample_date, crop, tillage, gas, flux FROM test.n2o_projects_fluxes")

    # Execute the query and fetch data
    with db.engine.connect() as conn:
        result = conn.execute(query)
        fluxes_data = result.fetchall()

    # Convert to DataFrame
    df = pd.DataFrame(fluxes_data, columns=['site', 'dataset', 'sample_date', 'crop', 'tillage', 'gas', 'flux'])

    # Ensure the sample_date is in datetime format
    df['sample_date'] = pd.to_datetime(df['sample_date'])

    # Group by dataset, gas, and find start and end dates
    df_grouped_gas = df.groupby(['dataset', 'gas']).agg(start_date=('sample_date', 'min'), end_date=('sample_date', 'max')).reset_index()

    # Create the Plotly Gantt chart by gas
    fig_gas = px.timeline(df_grouped_gas, x_start='start_date', x_end='end_date', y='dataset', color='gas', title='Sample Durations by Dataset and Gas', facet_row='gas')

    # Update the layout for better visibility
    fig_gas.update_layout(
        xaxis_title='Date',
        yaxis_title='Dataset',
        height=800,  # Adjust the height as needed
        margin=dict(l=20, r=20, t=40, b=20)
    )

    # Convert the Plotly figure to HTML
    graph_html_gas = pio.to_html(fig_gas, full_html=False)

    # Group by crop, dataset, and find start and end dates
    df_grouped_crop = df.groupby(['crop', 'dataset']).agg(start_date=('sample_date', 'min'), end_date=('sample_date', 'max')).reset_index()

    # Group by tillage, dataset, and find start and end dates
    df_grouped_tillage = df.groupby(['tillage', 'dataset']).agg(start_date= ('sample_date', 'min'), end_date = ('sample_date', 'max')).reset_index()

    # Create the Plotly Gantt chart by crop
    fig_crop = px.timeline(df_grouped_crop, x_start='start_date', x_end='end_date', y='dataset', color='crop', title='Sample Durations by Crop')

    fig_crop.update_traces(opacity=0.3)  # Set opacity to 60%

    # Update the layout for better visibility
    fig_crop.update_layout(
        xaxis_title='Date',
        yaxis_title='Crop',
        height=800,  # Adjust the height as needed
        margin=dict(l=20, r=20, t=40, b=20)
    )

    # Convert the Plotly figure to HTML
    graph_html_crop = pio.to_html(fig_crop, full_html=False)

    # Convert the Plotly figure to HTML
    graph_html_crop = pio.to_html(fig_crop, full_html=False) 

    ## Creat the Plotly Gantt chart by tillage
    fig_tillage = px.timeline(df_grouped_tillage, x_start = 'start_date', x_end = 'end_date', y = 'dataset', color = 'tillage', title = 'Sample Duration by Tillage')

    fig_tillage.update_traces(opacity=0.3)  # Set opacity to 60%

    # Update the layout for better visibility
    fig_tillage.update_layout(
        xaxis_title='Date',
        yaxis_title='Tillage',
        height=800,  # Adjust the height as needed
        margin=dict(l=20, r=20, t=40, b=20)
    )
   
    graph_html_tillage = pio.to_html(fig_tillage, full_html=False)
    

    # Render the graph in a simple HTML template
    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Fluxes Data Coverage</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        </head>
        <body>
            <h1>Fluxes Data Coverage by Gas</h1>
            {{ graph_html_gas|safe }}
            <h1>Fluxes Data Coverage by Crop</h1>
            {{ graph_html_crop|safe }}
                                  <h1>Fluxes Data Coverage by Tillage</h1>
                                  {{ graph_html_tillage|safe}}
        </body>
        </html>
    """, graph_html_gas=graph_html_gas, graph_html_crop=graph_html_crop, graph_html_tillage = graph_html_tillage)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

