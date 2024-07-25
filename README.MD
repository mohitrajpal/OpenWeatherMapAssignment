# OpenWeatherMap


## Prerequsites

- VPC created in AWS Account with connectivity to the internet via NatGateway for accessing OpenWeatherMap APIs
- Install AWS CLI(https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- Install terraform(https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)
- Install Python 3.x(https://wiki.python.org/moin/BeginnersGuide/Download)
- export aws credentials as environment variables

## Deployment Steps

- Clone the repository
- zip the python code in src directory
    ```sh
    cd src
    pip install -r requirements.txt
    zip -r owmLambda.zip .
    ```
- configure the following variables in terraform.tfvars
- bucket_name - name of the s3 bucket for remote state management
- table_name(name of the dynamodb table for remote state locking)
- owm_table_name(dynamodb table name for reading and writing OpenWeatherMap Data)
- vpcid(vpc id of the aws account)
- subnet_ids(private subnet ids of the vpc)
- vpc_cidr(vpc cidr range)
- api_key(api key to query OpenWeatherMap, set as senstive in variables.tf)
- s3_prefix(Managed s3 prefix list)
- dynamodb_prefix(Managed dynamodb prefix list)
- Run terraform commands
    ```sh
    terraform init
    terraform plan
    terraform apply
    ```

## Accessing the API
- terraform after successful execution outputs the API endpoint
- to access New York weather data the endpoint will be <api-endpoint>/test/getWeatherNyc
- API endpoint returns data in the following format
    ```sh
    {
    "Name": "New York",
    "Temperature(Celsius)": 23.81,
    "Humidity(Percentage)": 87,
    "Pressure(hPa)": 1017,
    "Wind_Speed(m/sec)": 3.09,
    "Description": "scattered clouds",
    "weather_time": "2024-07-24 05:45:17",
    "ingestion_time": "2024-07-24 05:49:49",
    "Average": "{\"Temperature_Average(Celsius)\": 25.19595238095238, \"Pressure_Average(hPa)\": 1016.5, \"Humidity_Average(Percentage)\": 72.11904761904762, \"Wind_Speed_Average(m/sec)\": 3.572619047619048}"
    }
    ```

