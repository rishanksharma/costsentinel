terraform{
    required_version=">=1.0"
}

variable "environment"{
    description= "Deployment environment"
    type= string
    default="dev"
}

variable "instance_type"{
    description="EC2 instance for the application"
    type=string
    default="t3.micro"
}

locals{
    project_name= "CostSentinel"

    common_tags={
        project=local.project_name
        environment= var.environment
        ManagedBy= "terraform"

    }
}

output "project_name"{
    value=local.project_name
}

output "selected_instance_type"{
    value=var.instance_type
}

output "resource_tags"{
    value= local.common_tags
}