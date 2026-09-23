type Vec2 = [x: number, y: number];
type ObservationOptions = { emit?: boolean };
type StateOptions = ObservationOptions & { disableDiffing?: boolean };
type StateAndScreenshot = { state: string; screenshot?: Uint8Array };
type PasteOptions = { format?: "text" | "md" | "html" };
type ClickOptions = { mouseButton?: MouseButton; clickCount?: number };
type SelectTextOptions = {
  prefix?: string;
  suffix?: string;
  selectionType?: SelectionType;
};
type Direction = "up" | "down" | "left" | "right" | "u" | "d" | "l" | "r";
type SelectionType = "text" | "cursor_before" | "cursor_after";
type MouseButton = "left" | "right" | "middle" | "l" | "r" | "m";

interface Target {
  getAXState(options?: StateOptions): Promise<string>;
  getScreenshot(options?: ObservationOptions): Promise<Uint8Array>;
  getAXStateAndScreenshot(options?: StateOptions): Promise<StateAndScreenshot>;
  paste(text: string, options?: PasteOptions): Promise<void>;
  click(target: number | Vec2, options?: ClickOptions): Promise<void>;
  drag(from: Vec2, to: Vec2): Promise<void>;
  pressKey(key: string): Promise<void>;
  scroll(target: number | Vec2, direction: Direction, pages?: number): Promise<void>;
  selectText(elementIndex: number, text: string, options?: SelectTextOptions): Promise<void>;
  setValue(elementIndex: number, value: string): Promise<void>;
  typeText(text: string): Promise<void>;
  performSecondaryAction(elementIndex: number, action: string): Promise<void>;
}

type AppInfo = {
  id: string;
  displayName?: string;
  lastUsedDate?: string;
  useCount?: number;
  isRunning?: boolean;
};

interface App extends Target {}

type BrowserInfo = {
  id: string;
  name?: string;
  family?: string;
  type?: "iab" | "extension" | "cdp";
  profileName?: string;
  metadata?: { extensionInstanceId?: string; codexSessionId?: string };
};

type BrowserTabInfo = {
  id: string;
  providerTabId?: string;
  title?: string;
  url?: string;
};

interface Browser {
  readonly browserId: string;
  documentation(): Promise<string>;
}

interface BrowserProvider {
  list(): Promise<BrowserInfo[]>;
  get(id: string): Promise<Browser>;
}

interface BrowserState extends BrowserInfo {
  tabs: BrowserTabInfo[];
}

type TabInfo = {
  id: string;
  providerTabId?: string;
  browserId: string;
  title?: string;
  url?: string;
};

type State = {
  apps: AppInfo[];
  browsers: BrowserState[];
  errors?: string[]; // Inventory failures; the other inventory remains usable.
};

type BrowserOptions = { browser?: string };
type GetBrowserOptions = { id?: string; url?: string };
type CreateBrowserTabOptions = { visible?: boolean; sessionName?: string };

interface Tab extends Target {
  readonly id: string;
  goto(url: string): Promise<void>;
  back(): Promise<void>;
  forward(): Promise<void>;
  reload(): Promise<void>;
  close(): Promise<void>;
  markDeliverable(): Promise<void>;
  markHandoff(): Promise<void>;
}

declare const cua: {
  getState(options?: ObservationOptions): Promise<State>;

  getApp(app: string): Promise<App>;
  listApps(options?: ObservationOptions): Promise<AppInfo[]>;

  /** Select without opening a tab. Use the returned browserId with createBrowserTab. */
  getBrowser(options?: GetBrowserOptions): Promise<Browser>;
  /** Apply options before opening the tab; omitted settings stay unchanged, unsupported settings throw. */
  createBrowserTab(
    browserId: string,
    url?: string,
    options?: CreateBrowserTabOptions,
  ): Promise<Tab>;
  getTab(id: string, options?: BrowserOptions): Promise<Tab>;
  listBrowsers(options?: ObservationOptions): Promise<BrowserInfo[]>;
  listTabs(options?: BrowserOptions & ObservationOptions): Promise<TabInfo[]>;
};
