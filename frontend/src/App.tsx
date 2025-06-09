import './App.css';
import ImageUploader from './components/ImageUploader';

function App() {
  return (
    <>
      <h1>CT 肺结节检测系统</h1>
      <div className="card">
        <ImageUploader />
      </div>
      <p className="read-the-docs">
        请上传您的 CT 影像以开始分析
      </p>
    </>
  );
}

export default App;
