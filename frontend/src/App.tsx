import './App.css';
import ImageUploader from './components/ImageUploader';
import logo from './assets/logo.jpeg';


function App() {
  return (
    <>
      <h1>CT 肺结节检测系统</h1>

      <div>
        <img src={logo} alt="logo" width={100} height={100}/>
      </div>

      <div className="card">
        {/* 图像上传组件（用户与系统交互的核心入口） */}
        <ImageUploader />
      </div>

      <p className="read-the-docs">
        请上传您的 CT 影像以开始分析
      </p>
    </>
  );
}

// 导出根组件（供index.tsx渲染到DOM）
export default App;