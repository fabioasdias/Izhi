import { useRef } from 'react';
import type { CommentReport } from '../types';

interface FileUploadProps {
  onUpload: (data: CommentReport) => void;
}

export function FileUpload({ onUpload }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleClick = () => {
    inputRef.current?.click();
  };

  const handleChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const text = await file.text();
      const data = JSON.parse(text) as CommentReport;

      if (!data.organization || !data.repositories) {
        throw new Error('Invalid JSON structure');
      }

      onUpload(data);
    } catch (err) {
      alert('Failed to parse JSON file. Please upload a valid report.');
      console.error(err);
    }

    if (inputRef.current) {
      inputRef.current.value = '';
    }
  };

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept=".json"
        onChange={handleChange}
        className="hidden"
      />
      <button
        onClick={handleClick}
        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
      >
        Upload JSON
      </button>
    </>
  );
}
