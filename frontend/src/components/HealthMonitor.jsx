import { useState, useEffect, useCallback } from 'react';
import { api } from '../api';
import './HealthMonitor.css';

export default function HealthMonitor() {
  const [clusterStatus, setClusterStatus] = useState(null);
  const [healthData, setHealthData] = useState(null);
  const [nodes, setNodes] = useState([]);
  const [models, setModels] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [error, setError] = useState(null);

  const loadHealthData = useCallback(async () => {
    try {
      setError(null);
      setIsLoading(true);
      
      // Load cluster status
      const status = await api.getClusterStatus();
      setClusterStatus(status);
      
      // Run health check
      const health = await api.runHealthCheck();
      setHealthData(health);
      
      // Load nodes
      const nodesData = await api.listNodes();
      setNodes(nodesData.nodes || []);
      
      // Load models
      const modelsData = await api.listModels();
      setModels(modelsData);
      
      setLastUpdate(new Date());
    } catch (err) {
      console.error('Failed to load health data:', err);
      setError(err.message || 'Failed to load health data');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadHealthData();
  }, [loadHealthData]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      loadHealthData();
    }, 10000); // Refresh every 10 seconds

    return () => clearInterval(interval);
  }, [autoRefresh, loadHealthData]);

  const formatTime = (dateString) => {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    return date.toLocaleTimeString();
  };

  const getHealthStatusClass = (isHealthy) => {
    return isHealthy ? 'healthy' : 'unhealthy';
  };

  const getHealthStatusIcon = (isHealthy) => {
    return isHealthy ? '✓' : '✗';
  };

  return (
    <div className="health-monitor">
      <div className="health-monitor-header">
        <h2>Model Health & Heartbeat Monitoring</h2>
        <div className="health-monitor-controls">
          <label className="auto-refresh-toggle">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh (10s)
          </label>
          <button
            className="refresh-btn"
            onClick={loadHealthData}
            disabled={isLoading}
          >
            {isLoading ? 'Refreshing...' : 'Refresh Now'}
          </button>
        </div>
      </div>

      {error && (
        <div className="health-error">
          Error: {error}
        </div>
      )}

      {lastUpdate && (
        <div className="last-update">
          Last updated: {formatTime(lastUpdate)}
        </div>
      )}

      {/* Cluster Overview */}
      {clusterStatus && (
        <div className="cluster-overview">
          <h3>Cluster Overview</h3>
          <div className="cluster-stats">
            <div className="stat">
              <span className="stat-label">Status:</span>
              <span className={`stat-value ${clusterStatus.status === 'ok' ? 'healthy' : 'unhealthy'}`}>
                {clusterStatus.status?.toUpperCase() || 'UNKNOWN'}
              </span>
            </div>
            <div className="stat">
              <span className="stat-label">Nodes Configured:</span>
              <span className="stat-value">{clusterStatus.nodes_configured || 0}</span>
            </div>
            <div className="stat">
              <span className="stat-label">Models Available:</span>
              <span className="stat-value">{clusterStatus.models_available || 0}</span>
            </div>
          </div>
        </div>
      )}

      {/* Health Check Results */}
      {healthData && (
        <div className="health-results">
          <h3>Node Health Status</h3>
          <div className="health-summary">
            <div className="summary-item">
              <span className="summary-label">Healthy Nodes:</span>
              <span className="summary-value healthy">
                {healthData.healthy_nodes || 0} / {healthData.total_nodes || 0}
              </span>
            </div>
            <div className="summary-item">
              <span className="summary-label">Overall Status:</span>
              <span className={`summary-value ${healthData.status === 'ok' ? 'healthy' : 'unhealthy'}`}>
                {healthData.status?.toUpperCase() || 'UNKNOWN'}
              </span>
            </div>
          </div>

          <div className="nodes-list">
            {Object.entries(healthData.nodes || {}).map(([nodeName, nodeHealth]) => (
              <div key={nodeName} className="node-card">
                <div className="node-header">
                  <div className="node-name">
                    <span className={`health-indicator ${getHealthStatusClass(nodeHealth.is_healthy)}`}>
                      {getHealthStatusIcon(nodeHealth.is_healthy)}
                    </span>
                    <span>{nodeName}</span>
                  </div>
                  <div className={`node-status ${getHealthStatusClass(nodeHealth.is_healthy)}`}>
                    {nodeHealth.is_healthy ? 'Healthy' : 'Unhealthy'}
                  </div>
                </div>
                
                <div className="node-details">
                  <div className="detail-row">
                    <span className="detail-label">Last Check:</span>
                    <span className="detail-value">{formatTime(nodeHealth.last_check)}</span>
                  </div>
                  
                  {nodeHealth.consecutive_failures > 0 && (
                    <div className="detail-row">
                      <span className="detail-label">Consecutive Failures:</span>
                      <span className="detail-value unhealthy">{nodeHealth.consecutive_failures}</span>
                    </div>
                  )}
                  
                  {nodeHealth.last_error && (
                    <div className="detail-row">
                      <span className="detail-label">Last Error:</span>
                      <span className="detail-value error-text">{nodeHealth.last_error}</span>
                    </div>
                  )}
                  
                  <div className="detail-row">
                    <span className="detail-label">Available Models:</span>
                    <div className="models-list">
                      {nodeHealth.available_models && nodeHealth.available_models.length > 0 ? (
                        nodeHealth.available_models.map((model, idx) => (
                          <span key={idx} className="model-tag">
                            {model}
                          </span>
                        ))
                      ) : (
                        <span className="no-models">No models available</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Node Configuration */}
      {nodes.length > 0 && (
        <div className="nodes-config">
          <h3>Node Configuration</h3>
          <div className="nodes-list">
            {nodes.map((node) => (
              <div key={node.name} className="node-config-card">
                <div className="node-header">
                  <div className="node-name">
                    <span>{node.name}</span>
                    {node.is_chairman && (
                      <span className="chairman-badge">Chairman</span>
                    )}
                  </div>
                  <div className={`node-enabled ${node.enabled ? 'enabled' : 'disabled'}`}>
                    {node.enabled ? 'Enabled' : 'Disabled'}
                  </div>
                </div>
                <div className="node-details">
                  <div className="detail-row">
                    <span className="detail-label">URL:</span>
                    <span className="detail-value">{node.host}:{node.port}</span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-label">Timeout:</span>
                    <span className="detail-value">{node.timeout}s</span>
                  </div>
                  {node.chairman_model && (
                    <div className="detail-row">
                      <span className="detail-label">Chairman Model:</span>
                      <span className="detail-value">{node.chairman_model}</span>
                    </div>
                  )}
                  <div className="detail-row">
                    <span className="detail-label">Configured Models:</span>
                    <div className="models-list">
                      {node.models && node.models.length > 0 ? (
                        node.models.map((model, idx) => (
                          <span key={idx} className="model-tag">
                            {model}
                          </span>
                        ))
                      ) : (
                        <span className="no-models">No models configured</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Models Overview */}
      {models && (
        <div className="models-overview">
          <h3>Models Overview</h3>
          <div className="models-summary">
            <div className="summary-item">
              <span className="summary-label">Total Models:</span>
              <span className="summary-value">{models.total_models || 0}</span>
            </div>
            {models.chairman && (
              <div className="summary-item">
                <span className="summary-label">Chairman Model:</span>
                <span className="summary-value">{models.chairman.model}</span>
                <span className="summary-subtext">({models.chairman.node_name})</span>
              </div>
            )}
          </div>
          {models.council_models && models.council_models.length > 0 && (
            <div className="all-models-list">
              {models.council_models.map((model, idx) => (
                <div key={idx} className="model-item">
                  <span className="model-name">{model.model}</span>
                  <span className="model-node">{model.node_name}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

