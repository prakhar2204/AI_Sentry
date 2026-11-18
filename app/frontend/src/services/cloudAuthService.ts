export type CloudProvider = 'aws' | 'azure' | 'gcp';
export interface CloudIdentity {
  provider: CloudProvider;
  account: string;
  identity: string;
  user_id?: string;
  region: string;
  profile?: string;
}
export interface CliStatus {
  provider: CloudProvider;
  available: boolean;
  implemented: boolean;
  version?: string;
  minimum_version?: string;
  install_url?: string;
  code: string;
  message: string;
}
export interface LoginOptions {
  region: string;
  mode?: 'console' | 'sso';
  remote?: boolean;
  start_url?: string;
  sso_region?: string;
  account?: string;
  role?: string;
  accessKeyId?: string;
  secretAccessKey?: string;
}
export interface CloudAuth {
  check_cli(): Promise<CliStatus>;
  login(options: LoginOptions): Promise<CloudIdentity>;
  whoami(region: string): Promise<CloudIdentity>;
  select_scope(identity: CloudIdentity): Promise<CloudIdentity>;
  logout(): Promise<void>;
  cancel(): Promise<void>;
}

export function cloudAuth(provider: CloudProvider): CloudAuth {
  async function invoke<T>(action: string, options: unknown = {}): Promise<T> {
    if (!window.electronAPI?.cloudAuth) throw new Error('Cloud sign-in requires the desktop app');
    const response = await window.electronAPI.cloudAuth({ provider, action, options });
    if (!response.ok) throw new Error(response.message || 'Cloud authentication failed');
    return response.result as T;
  }
  return {
    check_cli: () => invoke('check_cli'),
    login: options => invoke('login', options),
    whoami: region => invoke('whoami', { region }),
    select_scope: identity => invoke('select_scope', identity),
    logout: () => invoke('logout'),
    cancel: () => invoke('cancel'),
  };
}
