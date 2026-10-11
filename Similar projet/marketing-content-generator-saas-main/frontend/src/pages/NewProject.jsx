import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { projectsAPI } from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';

function NewProject() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    product_name: '',
    product_description: '',
    target_audience: '',
    unique_selling_points: [''],
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleUSPChange = (index, value) => {
    const newUSPs = [...formData.unique_selling_points];
    newUSPs[index] = value;
    setFormData({ ...formData, unique_selling_points: newUSPs });
  };

  const addUSP = () => {
    setFormData({
      ...formData,
      unique_selling_points: [...formData.unique_selling_points, ''],
    });
  };

  const removeUSP = (index) => {
    const newUSPs = formData.unique_selling_points.filter((_, i) => i !== index);
    setFormData({ ...formData, unique_selling_points: newUSPs });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    // Filter out empty USPs
    const cleanedData = {
      ...formData,
      unique_selling_points: formData.unique_selling_points.filter((usp) => usp.trim() !== ''),
    };

    if (cleanedData.unique_selling_points.length === 0) {
      setError('Please add at least one unique selling point');
      setLoading(false);
      return;
    }

    try {
      const response = await projectsAPI.create(cleanedData);
      navigate(`/projects/${response.data.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create project. Please try again.');
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <LoadingSpinner message="Generating your marketing content... This may take 1-2 minutes." />
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white rounded-xl shadow-lg p-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Create New Project</h1>
          <p className="text-gray-600 mb-8">
            Fill in the details about your product and we'll generate marketing content for all platforms
          </p>

          {error && (
            <div className="bg-red-50 text-red-600 p-4 rounded-lg mb-6">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="product_name" className="block text-sm font-medium text-gray-700 mb-2">
                Product Name *
              </label>
              <input
                type="text"
                id="product_name"
                name="product_name"
                value={formData.product_name}
                onChange={handleChange}
                required
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-600 focus:border-transparent"
                placeholder="e.g., Smart Water Bottle"
              />
            </div>

            <div>
              <label htmlFor="product_description" className="block text-sm font-medium text-gray-700 mb-2">
                Product Description *
              </label>
              <textarea
                id="product_description"
                name="product_description"
                value={formData.product_description}
                onChange={handleChange}
                required
                rows={4}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-600 focus:border-transparent"
                placeholder="Describe your product, its features, and benefits..."
              />
            </div>

            <div>
              <label htmlFor="target_audience" className="block text-sm font-medium text-gray-700 mb-2">
                Target Audience *
              </label>
              <textarea
                id="target_audience"
                name="target_audience"
                value={formData.target_audience}
                onChange={handleChange}
                required
                rows={3}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-600 focus:border-transparent"
                placeholder="e.g., Health-conscious professionals aged 25-40..."
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Unique Selling Points *
              </label>
              {formData.unique_selling_points.map((usp, index) => (
                <div key={index} className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={usp}
                    onChange={(e) => handleUSPChange(index, e.target.value)}
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-600 focus:border-transparent"
                    placeholder={`USP #${index + 1}`}
                  />
                  {formData.unique_selling_points.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeUSP(index)}
                      className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
                    >
                      Remove
                    </button>
                  )}
                </div>
              ))}
              <button
                type="button"
                onClick={addUSP}
                className="mt-2 text-primary-600 hover:text-primary-700 font-medium"
              >
                + Add Another USP
              </button>
            </div>

            <div className="flex gap-4 pt-4">
              <button
                type="button"
                onClick={() => navigate('/dashboard')}
                className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-700 py-3 rounded-lg font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex-1 bg-primary-600 hover:bg-primary-700 text-white py-3 rounded-lg font-semibold shadow-lg hover:shadow-xl transition-all"
              >
                Generate Content
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

export default NewProject;
