# Output the API gateway endpoint to invoke the OpenWeatherMap Lambda function
output endpoint {
  value       = aws_apigatewayv2_api.weatherapigateway.api_endpoint
}

