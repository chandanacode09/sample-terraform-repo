terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

resource "google_pubsub_topic" "test_999_dev_topic_091" {
  name = "test-999-dev-topic-091"
}

resource "google_storage_bucket" "my_new_bucket" {
  name          = "my-unique-test-bucket-12345" # You can change this name
  location      = var.region
  force_destroy = true # Be careful with this in production
}