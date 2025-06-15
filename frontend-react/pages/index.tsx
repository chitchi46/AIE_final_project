import { useState, useEffect } from 'react';
import { fetchStatus } from '../services/api';

export default function Home() {
  const [apiMessage, setApiMessage] = useState('Loading...');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchStatus().then((msg) => {
      setApiMessage(msg);
      setIsLoading(false);
    });
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-4 bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full">
        <h1 className="text-3xl font-bold mb-6 text-center text-gray-800">Q&A生成システム</h1>
        
        <div className="mb-6">
          <h2 className="text-lg font-semibold mb-2 text-gray-700">API接続状態</h2>
          <p className={`text-sm p-3 rounded ${isLoading ? 'bg-yellow-100 text-yellow-800' : apiMessage.includes('unreachable') ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}`}>
            {apiMessage}
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4">
          <div className="bg-blue-50 p-4 rounded-lg">
            <h3 className="font-semibold text-blue-800">🤖 AI自動生成</h3>
            <p className="text-sm text-blue-600">講義資料から自動でQ&Aを生成</p>
          </div>
          
          <div className="bg-green-50 p-4 rounded-lg">
            <h3 className="font-semibold text-green-800">📊 難易度調整</h3>
            <p className="text-sm text-green-600">易・中・難の3段階で調整可能</p>
          </div>
          
          <div className="bg-purple-50 p-4 rounded-lg">
            <h3 className="font-semibold text-purple-800">⚡ リアルタイム</h3>
            <p className="text-sm text-purple-600">即座の正誤判定とフィードバック</p>
          </div>
        </div>
      </div>
    </main>
  );
} 