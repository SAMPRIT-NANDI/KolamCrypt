import os
import shutil
from pathlib import Path
import config

class CloudStorageManager:
    """
    Manages fragment storage across simulated multi-cloud providers 
    (Google Drive, Dropbox, OneDrive) and extensible real cloud API adapters.
    """
    def __init__(self):
        config.ensure_directories()
        self.providers = config.CLOUD_SERVICES

    def get_provider_dir(self, cloud_service: str) -> Path:
        """Get local target directory for specified cloud service."""
        if cloud_service not in self.providers:
            # Default to Drive if unknown
            cloud_service = "GoogleDrive"
        return self.providers[cloud_service]

    def upload_fragment(self, fragment_source: str | bytes, cloud_service: str, target_filename: str = None) -> dict:
        """
        Upload fragment (from file path or raw bytes) to specified cloud provider.
        
        Returns dict metadata:
        {
            "cloud_service": cloud_service,
            "cloud_file_id": target_filename,
            "path": str(dest_path),
            "size": int
        }
        """
        target_dir = self.get_provider_dir(cloud_service)
        
        if isinstance(fragment_source, (str, Path)):
            src_path = Path(fragment_source)
            if not src_path.exists():
                raise FileNotFoundError(f"Fragment source path does not exist: {fragment_source}")
            filename = target_filename or src_path.name
            dest_path = target_dir / filename
            shutil.copy(src_path, dest_path)
            size = dest_path.stat().st_size
        elif isinstance(fragment_source, bytes):
            if not target_filename:
                raise ValueError("target_filename is required when uploading bytes.")
            filename = target_filename
            dest_path = target_dir / filename
            with open(dest_path, "wb") as f:
                f.write(fragment_source)
            size = len(fragment_source)
        else:
            raise TypeError("fragment_source must be a file path string or bytes.")

        return {
            "cloud_service": cloud_service,
            "cloud_file_id": filename,
            "path": str(dest_path),
            "size": size
        }

    def download_fragment(self, cloud_file_id: str, cloud_service: str, local_output_path: str = None) -> bytes:
        """
        Download fragment content from specified cloud provider.
        
        Returns raw fragment bytes and optionally writes to local_output_path.
        """
        target_dir = self.get_provider_dir(cloud_service)
        src_path = target_dir / cloud_file_id
        
        if not src_path.exists():
            raise FileNotFoundError(f"Fragment '{cloud_file_id}' not found in cloud '{cloud_service}'")
            
        with open(src_path, "rb") as f:
            data = f.read()
            
        if local_output_path:
            out_p = Path(local_output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            with open(out_p, "wb") as f:
                f.write(data)
                
        return data

    def delete_fragment(self, cloud_file_id: str, cloud_service: str) -> bool:
        """Delete fragment from specified cloud service."""
        target_dir = self.get_provider_dir(cloud_service)
        src_path = target_dir / cloud_file_id
        if src_path.exists():
            src_path.unlink()
            return True
        return False

    def list_cloud_fragments(self, cloud_service: str = None) -> list[dict]:
        """List all fragments present across cloud services."""
        results = []
        services_to_check = [cloud_service] if cloud_service in self.providers else list(self.providers.keys())
        
        for service in services_to_check:
            folder = self.providers[service]
            for file in folder.glob("*"):
                if file.is_file():
                    results.append({
                        "cloud_service": service,
                        "filename": file.name,
                        "path": str(file),
                        "size": file.stat().st_size
                    })
        return results

# Singleton instance
cloud_manager = CloudStorageManager()

def upload_fragment(fragment_source, cloud_service: str, target_filename: str = None) -> dict:
    return cloud_manager.upload_fragment(fragment_source, cloud_service, target_filename)

def download_fragment(cloud_file_id: str, cloud_service: str, local_output_path: str = None) -> bytes:
    return cloud_manager.download_fragment(cloud_file_id, cloud_service, local_output_path)

def delete_fragment(cloud_file_id: str, cloud_service: str) -> bool:
    return cloud_manager.delete_fragment(cloud_file_id, cloud_service)

if __name__ == "__main__":
    test_meta = upload_fragment(b"Test Cloud Fragment Data", "GoogleDrive", "test_frag1.dat")
    print(f"Uploaded to cloud: {test_meta}")
    downloaded = download_fragment("test_frag1.dat", "GoogleDrive")
    assert downloaded == b"Test Cloud Fragment Data"
    print("Cloud Storage Manager Module Verified Successfully.")
