project(
  'nautilus-7zip',
  version: '0.2.0',
  meson_version: '>=1.3.0',
)

gnome = import('gnome')
i18n = import('i18n')
python = import('python').find_installation('python3')

prefix = get_option('prefix')
bindir = get_option('bindir')
datadir = get_option('datadir')
localedir = get_option('localedir')

python.install_sources(
  files(
    'src/nautilus_7zip/__init__.py',
    'src/nautilus_7zip/application.py',
    'src/nautilus_7zip/backend.py',
    'src/nautilus_7zip/commands.py',
    'src/nautilus_7zip/diagnostics.py',
    'src/nautilus_7zip/i18n.py',
    'src/nautilus_7zip/labels.py',
    'src/nautilus_7zip/main.py',
    'src/nautilus_7zip/models.py',
    'src/nautilus_7zip/paths.py',
    'src/nautilus_7zip/progress.py',
    'src/nautilus_7zip/runner.py',
    'src/nautilus_7zip/runtime.py',
    'src/nautilus_7zip/selection.py',
    'src/nautilus_7zip/sizes.py',
  ),
  subdir: 'nautilus_7zip',
)

launcher_conf = configuration_data()
launcher_conf.set('PYTHON', python.full_path())
configure_file(
  input: 'data/nautilus-7zip.in',
  output: 'nautilus-7zip',
  configuration: launcher_conf,
  install: true,
  install_dir: bindir,
  install_mode: 'rwxr-xr-x',
)

nautilus_extension_dir = get_option('nautilus_extension_dir')
if nautilus_extension_dir == ''
  nautilus_extension_dir = join_paths(datadir, 'nautilus-python', 'extensions')
endif

install_data(
  'src/extension/nautilus_7zip_extension.py',
  install_dir: nautilus_extension_dir,
)

i18n.merge_file(
  input: 'data/io.github.michaelbrylevskii.Nautilus7Zip.desktop.in',
  output: 'io.github.michaelbrylevskii.Nautilus7Zip.desktop',
  type: 'desktop',
  po_dir: 'po',
  install: true,
  install_dir: join_paths(datadir, 'applications'),
)

install_data(
  'data/icons/hicolor/scalable/apps/io.github.michaelbrylevskii.Nautilus7Zip.svg',
  install_dir: join_paths(datadir, 'icons', 'hicolor', 'scalable', 'apps'),
)
install_data(
  'data/icons/hicolor/symbolic/apps/io.github.michaelbrylevskii.Nautilus7Zip-symbolic.svg',
  install_dir: join_paths(datadir, 'icons', 'hicolor', 'symbolic', 'apps'),
)

subdir('po')

gnome.post_install(
  gtk_update_icon_cache: true,
)

pytest = find_program('pytest', required: false)
if pytest.found()
  test(
    'pytest',
    pytest,
    args: ['-q'],
    workdir: meson.project_source_root(),
  )
else
  warning('pytest was not found; the Meson test target is disabled')
endif
