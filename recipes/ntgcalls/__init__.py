from pythonforandroid.recipe import CppCompiledComponentsPythonRecipe


class NtgcallsRecipe(CppCompiledComponentsPythonRecipe):
    version = '2.2.5'
    url = 'https://github.com/pytgcalls/ntgcalls/archive/refs/tags/v{version}.tar.gz'
    depends = ['python3', 'setuptools']
    site_packages_name = 'ntgcalls'
    call_hostpython_via_target = False

    def get_build_dir(self, arch):
        return super().get_build_dir(arch)

    def build_arch(self, arch):
        env = self.get_recipe_env(arch)
        import os

        build_dir = os.path.join(self.get_build_dir(arch), 'build')
        os.makedirs(build_dir, exist_ok=True)

        ndk = env.get('ANDROID_NDK_HOME', env.get('ANDROID_NDK', ''))
        if not ndk:
            for p in ['/usr/local/lib/android/sdk/ndk/25.2.9519653',
                       os.path.expanduser('~/android-ndk-r25b'),
                       os.path.expanduser('~/.buildozer/android/platform/android-ndk-r25b')]:
                if os.path.exists(p):
                    ndk = p
                    break

        if not ndk:
            self.warning('ANDROID_NDK not found, skipping ntgcalls build')
            return

        toolchain = os.path.join(ndk, 'build', 'cmake', 'android.toolchain.cmake')

        cmake_args = [
            'cmake',
            f'-DCMAKE_TOOLCHAIN_FILE={toolchain}',
            f'-DANDROID_ABI={arch.arch}',
            f'-DANDROID_PLATFORM=android-24',
            f'-DCMAKE_ANDROID_NDK={ndk}',
            '-DBUILD_SHARED_LIBS=ON',
            '-DCMAKE_BUILD_TYPE=Release',
            '..'
        ]

        self.run_cmake(cmake_args, build_dir, env)
        self.run_cmake(['cmake', '--build', build_dir, '--', '-j4'], build_dir, env)

        import glob
        for so in glob.glob(os.path.join(build_dir, '*.so')):
            self.install_python_package(arch, so)


recipe = NtgcallsRecipe()
