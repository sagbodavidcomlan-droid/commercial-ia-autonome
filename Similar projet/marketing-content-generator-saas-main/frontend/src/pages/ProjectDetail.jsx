import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { projectsAPI } from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';

function ProjectDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [activeTab, setActiveTab] = useState('facebook');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadProject();
  }, [id]);

  const loadProject = async () => {
    try {
      const response = await projectsAPI.get(id);
      setProject(response.data);
    } catch (err) {
      setError('Failed to load project');
    } finally {
      setLoading(false);
    }
  };

  const downloadContent = (platform, content) => {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${project.product_name}_${platform}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return <LoadingSpinner message="Loading project..." />;
  }

  if (error || !project) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 text-xl mb-4">{error || 'Project not found'}</p>
          <button
            onClick={() => navigate('/dashboard')}
            className="bg-primary-600 text-white px-6 py-2 rounded-lg"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const tabs = [
    { id: 'facebook', name: 'Facebook', icon: '📘' },
    { id: 'instagram', name: 'Instagram', icon: '📸' },
    { id: 'tiktok', name: 'TikTok', icon: '🎵' },
    { id: 'youtube', name: 'YouTube', icon: '🎬' },
    { id: 'google_ads', name: 'Google Ads', icon: '🔍' },
    { id: 'image_prompt', name: 'Image Prompt', icon: '🎨' },
  ];

  const getContent = (tab) => {
    if (tab === 'image_prompt') {
      return project.content?.creative?.image_prompt || 'No content generated';
    }
    return project.content?.content?.[tab] || 'No content generated';
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => navigate('/dashboard')}
            className="text-primary-600 hover:text-primary-700 mb-4 inline-flex items-center"
          >
            ← Back to Dashboard
          </button>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">{project.product_name}</h1>
          <p className="text-gray-600">{project.product_description}</p>
          <div className="mt-4 flex flex-wrap gap-4 text-sm">
            <div>
              <span className="font-semibold">Target Audience:</span> {project.target_audience}
            </div>
            <div>
              <span className="font-semibold">Created:</span>{' '}
              {new Date(project.created_at).toLocaleDateString()}
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-xl shadow-lg overflow-hidden">
          <div className="border-b border-gray-200">
            <div className="flex overflow-x-auto">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-6 py-4 font-medium whitespace-nowrap transition-colors ${
                    activeTab === tab.id
                      ? 'text-primary-600 border-b-2 border-primary-600 bg-primary-50'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  }`}
                >
                  <span className="mr-2">{tab.icon}</span>
                  {tab.name}
                </button>
              ))}
            </div>
          </div>

          {/* Content */}
          <div className="p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold text-gray-900">
                {tabs.find((t) => t.id === activeTab)?.name} Content
              </h2>
              <button
                onClick={() => downloadContent(activeTab, getContent(activeTab))}
                className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg font-medium"
              >
                Download
              </button>
            </div>
            <div className="bg-gray-50 rounded-lg p-6 whitespace-pre-wrap font-mono text-sm">
              {getContent(activeTab)}
            </div>
          </div>
        </div>

        {/* Research Section */}
        {project.content?.research && (
          <div className="mt-8 grid md:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h3 className="text-xl font-bold text-gray-900 mb-4">📊 Audience Insights</h3>
              <div className="text-gray-700 whitespace-pre-wrap">
                {project.content.research.audience_insights}
              </div>
            </div>
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h3 className="text-xl font-bold text-gray-900 mb-4">🎯 Competitor Analysis</h3>
              <div className="text-gray-700 whitespace-pre-wrap">
                {project.content.research.competitor_analysis}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ProjectDetail;
