# Configure the Google Cloud provider
provider "google" {
  project = "terraform-examples-gcloud"
  region  = "us-east1-b"
}

# Create a Google Compute instance
resource "google_compute_instance" "example" {
  name          = "example"
  machine_type  = "f1-micro"
  zone          = "us-east1-b"
  
  boot_disk {
    initialize_params {
      image = "ubuntu-1604-lts"
    }
  }
  
  network_interface {
    network = "default"

    access_config {
      // Ephemeral IP
    }
  }
}

# Create a Google Cloud Storage bucket
resource "google_storage_bucket" "sample_bucket" {
  name          = "sample-bucket-unique-name" # IMPORTANT: Change this to a globally unique name!
  location      = "US"
  force_destroy = false
}
