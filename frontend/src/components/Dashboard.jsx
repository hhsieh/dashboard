import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Line } from 'react-chartjs-2';

const Dashboard = () => {
  const [chartData, setChartData] = useState({});

  useEffect(() => {
    axios.get('http://localhost:5000/data')
      .then(response => {
        const data = response.data;
        setChartData({
          labels: data.map(d => d.id),
          datasets: [
            {
              label: 'Values',
              data: data.map(d => d.value),
              borderColor: 'rgba(75,192,192,1)',
              fill: false
            }
          ]
        });
      });
  }, []);

  return (
    <div>
      <h2>Dashboard</h2>
      <Line data={chartData} />
    </div>
  );
};

export default Dashboard;

