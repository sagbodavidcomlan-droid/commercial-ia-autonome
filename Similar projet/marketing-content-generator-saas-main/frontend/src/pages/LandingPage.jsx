import { Link } from 'react-router-dom';

function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-blue-100">
      {/* Hero Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-16">
        <div className="text-center">
          <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
            AI-Powered Marketing Content
            <span className="text-primary-600"> Generation</span>
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
            Generate professional marketing content for all platforms in minutes.
            From Facebook to TikTok, Instagram to Google Ads - powered by Claude AI.
          </p>
          <div className="flex gap-4 justify-center">
            <Link
              to="/register"
              className="bg-primary-600 hover:bg-primary-700 text-white px-8 py-3 rounded-lg text-lg font-semibold shadow-lg hover:shadow-xl transition-all"
            >
              Get Started Free
            </Link>
            <Link
              to="/login"
              className="bg-white hover:bg-gray-50 text-primary-600 px-8 py-3 rounded-lg text-lg font-semibold shadow-lg hover:shadow-xl transition-all"
            >
              Sign In
            </Link>
          </div>
        </div>

        {/* Features */}
        <div className="mt-20 grid md:grid-cols-3 gap-8">
          <div className="bg-white p-6 rounded-xl shadow-lg">
            <div className="text-4xl mb-4">🚀</div>
            <h3 className="text-xl font-bold mb-2">Multi-Platform Content</h3>
            <p className="text-gray-600">
              Generate optimized content for Facebook, Instagram, TikTok, YouTube, and Google Ads all at once.
            </p>
          </div>
          <div className="bg-white p-6 rounded-xl shadow-lg">
            <div className="text-4xl mb-4">🎯</div>
            <h3 className="text-xl font-bold mb-2">Audience-Focused</h3>
            <p className="text-gray-600">
              AI analyzes your target audience and creates content that resonates with their needs and preferences.
            </p>
          </div>
          <div className="bg-white p-6 rounded-xl shadow-lg">
            <div className="text-4xl mb-4">⚡</div>
            <h3 className="text-xl font-bold mb-2">Lightning Fast</h3>
            <p className="text-gray-600">
              What takes hours manually takes minutes with AI. Save time and focus on growing your business.
            </p>
          </div>
        </div>

        {/* Platforms */}
        <div className="mt-16 text-center">
          <h2 className="text-3xl font-bold text-gray-900 mb-8">
            One Tool, All Platforms
          </h2>
          <div className="flex flex-wrap justify-center gap-6">
            {['Facebook', 'Instagram', 'TikTok', 'YouTube', 'Google Ads'].map((platform) => (
              <div
                key={platform}
                className="bg-white px-6 py-3 rounded-full shadow-md font-semibold text-gray-700"
              >
                {platform}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default LandingPage;
