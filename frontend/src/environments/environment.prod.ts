// Ambiente de produção.
// apiBaseUrl VAZIO = mesma origem: o SPA e a API são servidos pelo mesmo host
// (condoguard.bluphy.com.br via CloudFront), que roteia /api/* para o ALB.
// Assim as chamadas viram caminhos relativos (/api/v1/...) e não há CORS.
export const environment = {
  production: true,
  apiBaseUrl: '',
};
