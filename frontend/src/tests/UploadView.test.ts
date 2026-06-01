import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import UploadView from '@/views/UploadView.vue'

// Control the upload call and router navigation.
const { uploadGifMock, pushMock } = vi.hoisted(() => ({
  uploadGifMock: vi.fn(),
  pushMock: vi.fn(),
}))
vi.mock('@/api/client', () => ({ uploadGif: uploadGifMock }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push: pushMock }) }))

function setFiles(input: HTMLInputElement, files: File[]) {
  Object.defineProperty(input, 'files', { value: files, configurable: true })
}

describe('UploadView', () => {
  beforeEach(() => {
    uploadGifMock.mockReset()
    pushMock.mockReset()
    // jsdom doesn't implement object URLs — stub them for the preview.
    globalThis.URL.createObjectURL = vi.fn(() => 'blob:preview-url')
    globalThis.URL.revokeObjectURL = vi.fn()
  })

  it('rejects non-.gif files with an error message', async () => {
    const wrapper = mount(UploadView)
    const input = wrapper.find('input[type="file"]')
    setFiles(input.element as HTMLInputElement, [
      new File(['data'], 'photo.png', { type: 'image/png' }),
    ])
    await input.trigger('change')

    expect(wrapper.text()).toContain('Only .gif files are allowed.')
    // No preview should be created for an invalid file.
    expect(wrapper.find('img').exists()).toBe(false)
  })

  it('shows a file preview after a valid .gif is selected', async () => {
    const wrapper = mount(UploadView)
    const input = wrapper.find('input[type="file"]')
    setFiles(input.element as HTMLInputElement, [
      new File(['gif-bytes'], 'dancing-cat.gif', { type: 'image/gif' }),
    ])
    await input.trigger('change')

    const preview = wrapper.find('img')
    expect(preview.exists()).toBe(true)
    expect(preview.attributes('src')).toBe('blob:preview-url')
    expect(wrapper.text()).toContain('Remove')
  })

  it('disables the submit button while uploading', async () => {
    // Keep the upload pending so the uploading state stays active.
    let resolveUpload: (value: unknown) => void = () => {}
    uploadGifMock.mockReturnValue(
      new Promise((resolve) => {
        resolveUpload = resolve
      }),
    )

    const wrapper = mount(UploadView)

    // Provide a valid file and a title so the form can be submitted.
    const input = wrapper.find('input[type="file"]')
    setFiles(input.element as HTMLInputElement, [
      new File(['gif-bytes'], 'clip.gif', { type: 'image/gif' }),
    ])
    await input.trigger('change')
    await wrapper.find('#title').setValue('My clip')

    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    const submit = wrapper.find('button[type="submit"]')
    expect(submit.attributes('disabled')).toBeDefined()
    expect(submit.text()).toContain('Uploading')
    expect(uploadGifMock).toHaveBeenCalledTimes(1)

    // Clean up the pending promise.
    resolveUpload({ id: 1 })
  })
})
