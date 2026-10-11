import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { projectsAPI } from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';

function Dashboard() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const response = await projectsAPI.list();
      setProjects(response.data);
    } catch (err) {
      setError('Failed to load projects');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this project?')) return;

    try {
      await projectsAPI.delete(id);
      setProjects(projects.filter((p) => p.id !== id));
    } catch (err) {
      alert('Failed to delete project');
    }
  };

  if (loading) {
    return <LoadingSpinner message="Loading your projects..." />;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">My Projects</h1>
            <p className="text-gray-600 mt-1">Manage your marketing content projects</p>
          </div>
          <Link
            to="/projects/new"
            className="bg-primary-600 hover:bg-primary-700 text-white px-6 py-3 rounded-lg font-semibold shadow-lg hover:shadow-xl transition-all"
          >
            + New Project
          </Link>
        </div>

        {error && (
          <div className="bg-red-50 text-red-600 p-4 rounded-lg mb-6">
            {error}
          </div>
        )}

        {projects.length === 0 ? (
          <div className="bg-white rounded-xl shadow-md p-12 text-center">
            <div className="text-6xl mb-4">📝</div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">No projects yet</h2>
            <p className="text-gray-600 mb-6">
              Create your first project to generate AI-powered marketing content
            </p>
            <Link
              to="/projects/new"
              className="inline-block bg-primary-600 hover:bg-primary-700 text-white px-8 py-3 rounded-lg font-semibold"
            >
              Create Your First Project
            </Link>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project) => (
              <div
                key={project.id}
                className="bg-white rounded-xl shadow-md hover:shadow-xl transition-all p-6"
              >
                <h3 className="text-xl font-bold text-gray-900 mb-2">
                  {project.product_name}
                </h3>
                <p className="text-gray-600 text-sm mb-4">
                  Target: {project.target_audience}
                </p>
                <p className="text-gray-500 text-xs mb-4">
                  Created: {new Date(project.created_at).toLocaleDateString()}
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => navigate(`/projects/${project.id}`)}
                    className="flex-1 bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg font-medium"
                  >
                    View
                  </button>
                  <button
                    onClick={() => handleDelete(project.id)}
                    className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg font-medium"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Dashboard;
