FROM mcr.microsoft.com/dotnet/aspnet:9.0 AS base
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
EXPOSE 5000

FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src

COPY ["*.csproj", "."]
RUN dotnet restore

COPY . .
RUN dotnet build -c Release -o /app/build

FROM build AS publish
RUN dotnet publish -c Release -o /app/publish /p:UseAppHost=false

FROM base AS final
WORKDIR /app
COPY --from=publish /app/publish .
COPY api-entrypoint.sh /usr/local/bin/api-entrypoint.sh
RUN chmod 0555 /usr/local/bin/api-entrypoint.sh

ENV ASPNETCORE_URLS=http://+:5000

ENTRYPOINT ["/usr/local/bin/api-entrypoint.sh"]
CMD ["dotnet", "ApiCore.dll"]
