import subprocess
import sys
import os

def install_requirements():
    """Install all required packages from requirements.txt."""
    print("\n=== Installing required packages ===\n")
    try:
        # Use pip to install requirements
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("\n✅ Successfully installed all required packages!")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error installing packages: {e}")
        return False
    return True

def check_azure_credentials():
    """Check if Azure credentials are set up."""
    print("\n=== Checking Azure credentials ===\n")
    
    # Check if secrets.toml exists
    secrets_dir = os.path.join('.streamlit')
    secrets_file = os.path.join(secrets_dir, 'secrets.toml')
    
    if not os.path.exists(secrets_dir):
        os.makedirs(secrets_dir)
        print("Created .streamlit directory")
    
    if os.path.exists(secrets_file):
        print("✅ .streamlit/secrets.toml file exists")
        # Optional: validate the file content
        with open(secrets_file, 'r') as f:
            content = f.read()
            if '[azure]' in content and 'endpoint' in content and 'key' in content:
                print("✅ Azure credentials appear to be properly configured")
            else:
                print("⚠️ Azure credentials may not be properly configured")
                create_secrets_template()
    else:
        print("❌ .streamlit/secrets.toml file not found")
        create_secrets_template()
    
def create_secrets_template():
    """Create a template for secrets.toml file."""
    secrets_file = os.path.join('.streamlit', 'secrets.toml')
    
    template = """[azure]
endpoint = "YOUR_AZURE_ENDPOINT"
key = "YOUR_AZURE_KEY"
"""
    
    with open(secrets_file, 'w') as f:
        f.write(template)
    
    print(f"\n✅ Created template at {secrets_file}")
    print("⚠️ Please edit this file and add your Azure Document Intelligence endpoint and key")

def setup_workspace():
    """Set up the complete workspace."""
    print("\n=== Document Validator Setup ===\n")
    
    # Make sure uploads directory exists
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
        print("✅ Created uploads directory")
    else:
        print("✅ Uploads directory already exists")
    
    # Install requirements
    if install_requirements():
        # Check Azure credentials
        check_azure_credentials()
        
        print("\n=== Setup Complete ===\n")
        print("To run the application, use:")
        print("\n    streamlit run app.py\n")

if __name__ == "__main__":
    setup_workspace()
