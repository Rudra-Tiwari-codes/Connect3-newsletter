import Head from 'next/head';

export default function Home() {
  return (
    <>
      <Head>
        <title>Event Newsletter System</title>
        <meta name="description" content="Automated personalized event newsletters" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <main className="min-h-screen bg-gradient-to-br from-purple-600 to-blue-600">
        <div className="container mx-auto px-4 py-16">
          <div className="max-w-4xl mx-auto bg-white rounded-2xl shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="bg-gradient-to-r from-purple-500 to-blue-500 p-8 text-white">
              <h1 className="text-4xl font-bold mb-2">Event Newsletter System</h1>
              <p className="text-xl opacity-90">
                Personalized event recommendations powered by AI and Machine Learning
              </p>
            </div>

            {/* Content */}
            <div className="p-8">
              <div className="mb-8">
                <h2 className="text-2xl font-bold text-gray-800 mb-4">How It Works</h2>
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="bg-blue-50 p-6 rounded-lg">
                    <div className="text-3xl mb-3">🤖</div>
                    <h3 className="font-bold text-lg mb-2">AI Classification</h3>
                    <p className="text-gray-600">
                      Events are automatically categorized using OpenAI GPT-4 into 13 different categories
                    </p>
                  </div>

                  <div className="bg-purple-50 p-6 rounded-lg">
                    <div className="text-3xl mb-3">📊</div>
                    <h3 className="font-bold text-lg mb-2">PCA Clustering</h3>
                    <p className="text-gray-600">
                      Users are grouped into tribes based on their preferences using Principal Component Analysis
                    </p>
                  </div>

                  <div className="bg-green-50 p-6 rounded-lg">
                    <div className="text-3xl mb-3">🎯</div>
                    <h3 className="font-bold text-lg mb-2">Smart Scoring</h3>
                    <p className="text-gray-600">
                      Events ranked by: (Cluster Match × 50) + (30 - Days Until Event)
                    </p>
                  </div>

                  <div className="bg-yellow-50 p-6 rounded-lg">
                    <div className="text-3xl mb-3">📧</div>
                    <h3 className="font-bold text-lg mb-2">Personalized Emails</h3>
                    <p className="text-gray-600">
                      Weekly newsletters with your top 10 event recommendations via SendGrid
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-gray-50 p-6 rounded-lg mb-8">
                <h2 className="text-2xl font-bold text-gray-800 mb-4">Tech Stack</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-center">
                    <div className="font-semibold">Database</div>
                    <div className="text-sm text-gray-600">Supabase</div>
                  </div>
                  <div className="text-center">
                    <div className="font-semibold">Backend</div>
                    <div className="text-sm text-gray-600">Next.js 14</div>
                  </div>
                  <div className="text-center">
                    <div className="font-semibold">AI</div>
                    <div className="text-sm text-gray-600">OpenAI</div>
                  </div>
                  <div className="text-center">
                    <div className="font-semibold">Email</div>
                    <div className="text-sm text-gray-600">SendGrid</div>
                  </div>
                </div>
              </div>

              <div className="bg-blue-50 p-6 rounded-lg">
                <h2 className="text-2xl font-bold text-gray-800 mb-4">Getting Started</h2>
                <ol className="list-decimal list-inside space-y-2 text-gray-700">
                  <li>Set up your environment variables in <code className="bg-white px-2 py-1 rounded">.env</code></li>
                  <li>Run database setup: <code className="bg-white px-2 py-1 rounded">npm run db:setup</code></li>
                  <li>Classify events: <code className="bg-white px-2 py-1 rounded">npm run ingest</code></li>
                  <li>Update clusters: <code className="bg-white px-2 py-1 rounded">npm run cluster</code></li>
                  <li>Send newsletters: <code className="bg-white px-2 py-1 rounded">npm run send</code></li>
                </ol>
              </div>
            </div>

            {/* Footer */}
            <div className="bg-gray-100 p-6 text-center text-gray-600">
              <p>Automated Event Newsletter System &copy; 2024</p>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
