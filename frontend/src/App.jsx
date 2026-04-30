import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, AreaChart, Area, PieChart, Pie, Cell
} from 'recharts';
import { Activity, Droplets, Thermometer, Zap, AlertTriangle, CheckCircle, ShieldAlert, Info } from 'lucide-react';
import { motion } from 'framer-motion';

const App = () => {
  const [data, setData] = useState([]);
  const [latest, setLatest] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get('/api/history');
        const history = response.data.history;
        if (history && history.length > 0) {
          const formattedData = history.map(item => ({
            time: new Date(item.timestamp).toLocaleTimeString(),
            ph: item.sensor_data?.ph || 0,
            temperature: item.sensor_data?.temperature || 0,
            turbidity: item.sensor_data?.turbidity || 0,
            tds: item.sensor_data?.tds || 0,
            contamination: item.contamination_level || 0,
            quality: item.quality
          })).reverse();
          
          setData(formattedData);
          setLatest(history[0]);
        }
        setLoading(false);
      } catch (error) {
        console.error("Error fetching data:", error);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (quality) => {
    return quality === 'Safe' ? 
      <CheckCircle className="status-safe" size={48} /> : 
      <ShieldAlert className="status-unsafe" size={48} />;
  };

  if (loading) return <div className="dashboard-container">Analyzing Water Quality...</div>;

  const contaminationData = [
    { name: 'Contamination', value: latest?.contamination_level * 100 },
    { name: 'Purity', value: (1 - latest?.contamination_level) * 100 }
  ];

  const COLORS = [latest?.quality === 'Safe' ? '#22c55e' : '#ef4444', '#334155'];

  return (
    <div className="dashboard-container">
      {/* Critical Alert Banner */}
      {latest?.quality !== 'Safe' && (
        <motion.div 
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          style={{ 
            backgroundColor: '#ef4444', 
            color: 'white', 
            padding: '1.5rem', 
            borderRadius: '12px', 
            marginBottom: '2rem',
            display: 'flex',
            alignItems: 'center',
            gap: '1.5rem',
            boxShadow: '0 10px 15px -3px rgba(239, 68, 68, 0.4)'
          }}
        >
          <ShieldAlert size={48} strokeWidth={2.5} />
          <div style={{ flex: 1 }}>
            <h2 style={{ margin: 0, fontSize: '1.5rem', fontWeight: '800' }}>CRITICAL CONTAMINATION ALERT</h2>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.5rem' }}>
              {latest?.reasons?.map((reason, idx) => (
                <span key={idx} style={{ backgroundColor: 'rgba(0,0,0,0.2)', padding: '0.4rem 0.8rem', borderRadius: '20px', fontSize: '0.9rem', fontWeight: '600' }}>
                  • {reason}
                </span>
              ))}
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <p style={{ margin: 0, opacity: 0.8, fontSize: '0.8rem' }}>ACTION REQUIRED</p>
            <h3 style={{ margin: 0 }}>DO NOT DRINK</h3>
          </div>
        </motion.div>
      )}

      <motion.div 
        initial={{ opacity: 0, y: -50 }}
        animate={{ opacity: 1, y: 0 }}
        style={{ textAlign: 'center', marginBottom: '3rem' }}
      >
        <h1 style={{ fontSize: '3rem', fontWeight: '800', background: 'linear-gradient(to right, #60a5fa, #a78bfa)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          Water Guard AI
        </h1>
        <p style={{ color: '#94a3b8', fontSize: '1.2rem' }}>Real-time Monitoring & Contamination Analysis</p>
      </motion.div>

      <div className="grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
        {/* Potability Statement Card */}
        <motion.div whileHover={{ scale: 1.01 }} className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', borderLeft: `8px solid ${latest?.quality === 'Safe' ? '#22c55e' : '#ef4444'}` }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1.5rem' }}>
            <div style={{ marginTop: '0.5rem' }}>{getStatusIcon(latest?.quality)}</div>
            <div style={{ flex: 1 }}>
              <h3 style={{ margin: 0, color: '#94a3b8' }}>Current Assessment</h3>
              <h1 style={{ fontSize: '2.8rem', margin: '0.5rem 0' }}>{latest?.quality === 'Safe' ? 'SAFE WATER' : 'CONTAMINATED'}</h1>
              <p style={{ margin: '0 0 1rem 0', fontSize: '1.1rem', color: '#cbd5e1' }}>
                {latest?.quality === 'Safe' ? 
                  "This water source is verified potable and safe for immediate use." : 
                  "High contamination detected! This water is unsafe for consumption."}
              </p>
              
              {/* Contamination Reasons */}
              {latest?.reasons && latest.reasons.length > 0 && (
                <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', padding: '1rem', borderRadius: '8px', borderLeft: '4px solid #ef4444' }}>
                  <h4 style={{ margin: '0 0 0.5rem 0', color: '#fca5a5', fontSize: '0.9rem', textTransform: 'uppercase' }}>Analysis Insights</h4>
                  <ul style={{ margin: 0, paddingLeft: '1.2rem', color: '#f87171', fontSize: '0.95rem' }}>
                    {latest.reasons.map((reason, idx) => (
                      <li key={idx} style={{ marginBottom: '0.25rem' }}>{reason}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </motion.div>

        {/* Contamination Gauge Card */}
        <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ flex: 1 }}>
            <h3 style={{ color: '#94a3b8' }}>Contamination Level</h3>
            <h1 style={{ fontSize: '3.5rem', margin: '0.5rem 0' }}>{(latest?.contamination_level * 100).toFixed(1)}%</h1>
            <span className={`badge badge-${latest?.quality?.toLowerCase()}`}>
              {(latest?.potability_score * 100).toFixed(1)}% ML Confidence
            </span>
          </div>
          <div style={{ width: 150, height: 150 }}>
            <ResponsiveContainer>
              <PieChart>
                <Pie
                  data={contaminationData}
                  innerRadius={50}
                  outerRadius={70}
                  paddingAngle={5}
                  dataKey="value"
                  startAngle={90}
                  endAngle={-270}
                >
                  {contaminationData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Sensor Data Icons Grid */}
      <div className="grid" style={{ marginTop: '2rem' }}>
        {[
          { label: 'pH Value', val: latest?.sensor_data?.ph?.toFixed(2), icon: <Droplets />, color: '#60a5fa' },
          { label: 'Temperature', val: `${latest?.sensor_data?.temperature?.toFixed(1)}°C`, icon: <Thermometer />, color: '#f87171' },
          { label: 'Turbidity', val: latest?.sensor_data?.turbidity?.toFixed(2), icon: <Activity />, color: '#fbbf24' },
          { label: 'TDS (Solids)', val: `${latest?.sensor_data?.tds?.toFixed(0)} ppm`, icon: <Zap />, color: '#a78bfa' }
        ].map((item, i) => (
          <div key={i} className="card" style={{ textAlign: 'center' }}>
            <div style={{ color: item.color, marginBottom: '0.5rem', display: 'flex', justifyContent: 'center' }}>{item.icon}</div>
            <p style={{ margin: 0, color: '#94a3b8' }}>{item.label}</p>
            <h2 style={{ margin: '0.5rem 0' }}>{item.val}</h2>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid" style={{ marginTop: '2rem' }}>
        <div className="chart-container">
          <h3>pH & Temperature Trends</h3>
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer>
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="time" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }} />
                <Legend />
                <Line type="monotone" dataKey="ph" stroke="#60a5fa" strokeWidth={3} dot={false} />
                <Line type="monotone" dataKey="temperature" stroke="#f87171" strokeWidth={3} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="chart-container">
          <h3>TDS & Turbidity Analysis</h3>
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer>
              <AreaChart data={data}>
                <defs>
                  <linearGradient id="colorTds" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#a78bfa" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#a78bfa" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="time" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }} />
                <Area type="monotone" dataKey="tds" stroke="#a78bfa" fillOpacity={1} fill="url(#colorTds)" />
                <Area type="monotone" dataKey="turbidity" stroke="#fbbf24" fillOpacity={0} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div style={{ textAlign: 'center', color: '#64748b', margin: '4rem 0' }}>
        <p><Info size={16} /> Sensor Node: {latest?.sensor_id} | Refined Analysis Mode (4-Feature ML)</p>
        <p>System Sync: {new Date(latest?.timestamp).toLocaleString()}</p>
      </div>
    </div>
  );
};

export default App;
