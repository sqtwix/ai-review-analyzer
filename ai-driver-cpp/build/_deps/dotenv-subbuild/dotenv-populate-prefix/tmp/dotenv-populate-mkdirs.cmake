# Distributed under the OSI-approved BSD 3-Clause License.  See accompanying
# file Copyright.txt or https://cmake.org/licensing for details.

cmake_minimum_required(VERSION ${CMAKE_VERSION}) # this file comes with cmake

# If CMAKE_DISABLE_SOURCE_CHANGES is set to true and the source directory is an
# existing directory in our source tree, calling file(MAKE_DIRECTORY) on it
# would cause a fatal error, even though it would be a no-op.
if(NOT EXISTS "/home/shurik/Documents/Projects/ai-review-analyzer/ai-driver-cpp/build/_deps/dotenv-src")
  file(MAKE_DIRECTORY "/home/shurik/Documents/Projects/ai-review-analyzer/ai-driver-cpp/build/_deps/dotenv-src")
endif()
file(MAKE_DIRECTORY
  "/home/shurik/Documents/Projects/ai-review-analyzer/ai-driver-cpp/build/_deps/dotenv-build"
  "/home/shurik/Documents/Projects/ai-review-analyzer/ai-driver-cpp/build/_deps/dotenv-subbuild/dotenv-populate-prefix"
  "/home/shurik/Documents/Projects/ai-review-analyzer/ai-driver-cpp/build/_deps/dotenv-subbuild/dotenv-populate-prefix/tmp"
  "/home/shurik/Documents/Projects/ai-review-analyzer/ai-driver-cpp/build/_deps/dotenv-subbuild/dotenv-populate-prefix/src/dotenv-populate-stamp"
  "/home/shurik/Documents/Projects/ai-review-analyzer/ai-driver-cpp/build/_deps/dotenv-subbuild/dotenv-populate-prefix/src"
  "/home/shurik/Documents/Projects/ai-review-analyzer/ai-driver-cpp/build/_deps/dotenv-subbuild/dotenv-populate-prefix/src/dotenv-populate-stamp"
)

set(configSubDirs )
foreach(subDir IN LISTS configSubDirs)
    file(MAKE_DIRECTORY "/home/shurik/Documents/Projects/ai-review-analyzer/ai-driver-cpp/build/_deps/dotenv-subbuild/dotenv-populate-prefix/src/dotenv-populate-stamp/${subDir}")
endforeach()
if(cfgdir)
  file(MAKE_DIRECTORY "/home/shurik/Documents/Projects/ai-review-analyzer/ai-driver-cpp/build/_deps/dotenv-subbuild/dotenv-populate-prefix/src/dotenv-populate-stamp${cfgdir}") # cfgdir has leading slash
endif()
